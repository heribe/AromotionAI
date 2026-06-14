"""
Unit tests for Analysis API endpoints (M4.3 / M4.4)。

测试策略：
- 使用 conftest.py 的 client fixture（基于真实 FastAPI app + 测试 DB）
- 通过 dependency_overrides 注入 mock AnalysisService，避免触发真实管道
- Cookie 通过 CookieService 真实写入测试 DB
- SSE 测试通过 client.stream() 消费事件流

R2 三问自检：
1. 契约闭环：每个测试断言 HTTP 状态码、响应结构 code/data 字段；
   覆盖 §2.1-2.7 中可自动测试的路径。
2. 对称性：每个创建任务的测试都有对应的清理（DB function fixture
   每个 case 重建 schema），SSE 订阅者退出时由 TaskManager finally 块清理。
3. 外部时序：mock AnalysisService 立即完成，事件按 emit 顺序到达；
   使用 task_manager 单例的事件缓冲避免订阅者丢事件。
"""

import os
import json
import uuid
import asyncio
import pytest
import datetime
from typing import AsyncIterator

# 统一使用时区感知的 UTC 时间，避免 datetime.utcnow() 弃用警告
def _now():
    return datetime.datetime.now(datetime.timezone.utc)
from unittest.mock import AsyncMock, MagicMock

# 在导入 app 之前设置 mock 模式，避免触发真实 HTTP/Playwright 调用
os.environ.setdefault("AROMOTION_TEST_MODE", "mock")

from fastapi.testclient import TestClient

from app.main import app
from app.database import get_db
from app.core.task_manager import TaskManager
from app.api.deps import get_task_manager, get_analysis_service
from app.models.analysis import AnalysisTask
from app.models.profile import ProfileReport
from app.services.cookie_service import CookieService
from app.services.task_service import TaskService


# ---------- helpers ----------

@pytest.fixture
def fresh_task_manager():
    """每个测试使用独立的 TaskManager 实例，避免单例状态污染。"""
    return TaskManager()


@pytest.fixture
def upload_douyin_cookie(db):
    """预置一个有效的抖音 Cookie。"""
    cookie_service = CookieService()
    asyncio.run(
        cookie_service.update_or_create_cookie(
            db=db,
            platform="douyin",
            cookie_data=[{"name": "sessionid", "value": "test-session"}],
            is_valid=True,
        )
    )
    return True


def _override_task_manager(tm: TaskManager):
    app.dependency_overrides[get_task_manager] = lambda: tm


def _override_analysis_service():
    """注入一个 mock AnalysisService：run_analysis 不做任何事，仅等待取消。"""
    mock_service = MagicMock()
    # 用一个永不主动结束的协程，让 cancel 路径有意义
    async def _never_end(self, task_id):
        try:
            await asyncio.sleep(30)
        except asyncio.CancelledError:
            raise
    mock_service.run_analysis = lambda task_id: _never_end(mock_service, task_id)
    app.dependency_overrides[get_analysis_service] = lambda: mock_service
    return mock_service


def _parse_sse_events(text: str) -> list[dict]:
    """把原始 SSE 文本解析为 [{'type': ..., 'data': ...}, ...]。"""
    events = []
    current = {}
    for line in text.split("\n"):
        line = line.rstrip("\r")
        if not line:
            if current:
                events.append(current)
                current = {}
            continue
        if line.startswith("event:"):
            current["type"] = line[len("event:"):].strip()
        elif line.startswith("data:"):
            raw = line[len("data:"):].strip()
            try:
                current["data"] = json.loads(raw)
            except json.JSONDecodeError:
                current["data"] = raw
    if current:
        events.append(current)
    return events


# ---------- F2: 创建任务 ----------

def test_create_task_standard(client, db, upload_douyin_cookie, fresh_task_manager):
    _override_task_manager(fresh_task_manager)
    _override_analysis_service()
    try:
        payload = {
            "blogger_url": "https://www.douyin.com/user/MS4wLjABAAA_test1",
            "platform": "douyin",
            "analysis_level": "standard",
        }
        resp = client.post("/api/v1/analysis/create", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == 0
        assert "task_id" in data["data"]
        assert data["data"]["status"] == "pending"
    finally:
        app.dependency_overrides.pop(get_task_manager, None)
        app.dependency_overrides.pop(get_analysis_service, None)


def test_create_task_auto_detect_platform(client, db, upload_douyin_cookie, fresh_task_manager):
    _override_task_manager(fresh_task_manager)
    _override_analysis_service()
    try:
        payload = {
            "blogger_url": "https://www.douyin.com/user/MS4wLjABAAA_auto",
            "platform": "auto",
            "analysis_level": "standard",
        }
        resp = client.post("/api/v1/analysis/create", json=payload)
        assert resp.status_code == 200
        task_id = resp.json()["data"]["task_id"]
        detail = client.get(f"/api/v1/analysis/{task_id}").json()
        assert detail["data"]["platform"] == "douyin"
    finally:
        app.dependency_overrides.pop(get_task_manager, None)
        app.dependency_overrides.pop(get_analysis_service, None)


def test_create_task_invalid_url(client, db, upload_douyin_cookie, fresh_task_manager):
    _override_task_manager(fresh_task_manager)
    try:
        payload = {
            "blogger_url": "not-a-valid-url",
            "platform": "douyin",
            "analysis_level": "standard",
        }
        resp = client.post("/api/v1/analysis/create", json=payload)
        # Pydantic 422 (字段验证) 或 API 400
        assert resp.status_code in (400, 422)
    finally:
        app.dependency_overrides.pop(get_task_manager, None)


def test_create_task_unsupported_platform(client, db, upload_douyin_cookie):
    payload = {
        "blogger_url": "https://instagram.com/p/somepost",
        "platform": "instagram",
        "analysis_level": "standard",
    }
    resp = client.post("/api/v1/analysis/create", json=payload)
    assert resp.status_code in (400, 422)


def test_create_task_missing_cookie(client, db, fresh_task_manager):
    """Cookie 不存在时应 400。需同时清理磁盘回退文件，否则 CookieService
    会从 data/test_cookies/{platform}.json 回读到 DB。"""
    _override_task_manager(fresh_task_manager)
    # 清理 DB + 磁盘残留
    from app.services.cookie_service import CookieService
    asyncio.run(CookieService().delete_cookie(db, "douyin"))
    cookie_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "test_cookies")
    disk_file = os.path.join(cookie_dir, "douyin.json")
    if os.path.exists(disk_file):
        os.remove(disk_file)
    try:
        payload = {
            "blogger_url": "https://www.douyin.com/user/MS4wLjABAAA_nocookie",
            "platform": "douyin",
            "analysis_level": "standard",
        }
        resp = client.post("/api/v1/analysis/create", json=payload)
        assert resp.status_code == 400
        assert "cookie" in resp.json()["detail"].lower()
    finally:
        app.dependency_overrides.pop(get_task_manager, None)


def test_create_task_custom_missing_config(client, db, upload_douyin_cookie):
    payload = {
        "blogger_url": "https://www.douyin.com/user/MS4wLjABAAA_custom_missing",
        "platform": "douyin",
        "analysis_level": "custom",
        "custom_config": None,
    }
    resp = client.post("/api/v1/analysis/create", json=payload)
    assert resp.status_code in (400, 422)


def test_create_task_custom_out_of_bounds(client, db, upload_douyin_cookie):
    payload = {
        "blogger_url": "https://www.douyin.com/user/MS4wLjABAAA_oob",
        "platform": "douyin",
        "analysis_level": "custom",
        "custom_config": {
            "post_selection": {"top_count": 500, "recent_count": -5},
        },
    }
    resp = client.post("/api/v1/analysis/create", json=payload)
    assert resp.status_code in (400, 422)


# ---------- F3: 任务详情 / 列表 / 取消 ----------

def _seed_pending_task(db) -> AnalysisTask:
    task = AnalysisTask(
        id=str(uuid.uuid4()),
        platform="douyin",
        blogger_url="https://www.douyin.com/user/MS4wLjABAAA_seed",
        analysis_level="standard",
        status="pending",
        progress=0,
        current_step="准备开始",
        created_at=_now(),
        updated_at=_now(),
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


def test_get_task_details(client, db, upload_douyin_cookie):
    task = _seed_pending_task(db)
    resp = client.get(f"/api/v1/analysis/{task.id}")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["task_id"] == task.id
    assert data["status"] == "pending"
    assert data["blogger_url"].startswith("https://")


def test_get_nonexistent_task(client, db):
    fake_id = str(uuid.uuid4())
    resp = client.get(f"/api/v1/analysis/{fake_id}")
    assert resp.status_code == 404


def test_list_tasks(client, db, upload_douyin_cookie):
    _seed_pending_task(db)
    resp = client.get("/api/v1/analysis/list?page=1&page_size=10")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["total"] >= 1
    assert len(data["items"]) >= 1
    assert data["page"] == 1
    assert data["page_size"] == 10


def test_list_tasks_filter_by_status(client, db, upload_douyin_cookie):
    t1 = _seed_pending_task(db)
    t2 = AnalysisTask(
        id=str(uuid.uuid4()),
        platform="douyin",
        blogger_url="https://www.douyin.com/user/x",
        analysis_level="standard",
        status="completed",
        progress=100,
        current_step="完成",
        created_at=_now(),
        updated_at=_now(),
        completed_at=_now(),
    )
    db.add(t2)
    db.commit()

    resp = client.get("/api/v1/analysis/list?status=completed")
    assert resp.status_code == 200
    items = resp.json()["data"]["items"]
    assert all(i["status"] == "completed" for i in items)
    assert any(i["task_id"] == t2.id for i in items)


def test_cancel_pending_task(client, db, upload_douyin_cookie, fresh_task_manager):
    _override_task_manager(fresh_task_manager)
    try:
        task = _seed_pending_task(db)
        resp = client.post(f"/api/v1/analysis/{task.id}/cancel")
        assert resp.status_code == 200
        assert resp.json()["code"] == 0
        # 二次查询确认状态
        detail = client.get(f"/api/v1/analysis/{task.id}").json()
        assert detail["data"]["status"] == "cancelled"
    finally:
        app.dependency_overrides.pop(get_task_manager, None)


def test_cancel_completed_task_rejected(client, db, upload_douyin_cookie):
    task = AnalysisTask(
        id=str(uuid.uuid4()),
        platform="douyin",
        blogger_url="https://www.douyin.com/user/x",
        analysis_level="standard",
        status="completed",
        progress=100,
        current_step="完成",
        created_at=_now(),
        updated_at=_now(),
        completed_at=_now(),
    )
    db.add(task)
    db.commit()

    resp = client.post(f"/api/v1/analysis/{task.id}/cancel")
    assert resp.status_code == 400
    assert "completed" in resp.json()["detail"].lower()


def test_double_cancel_rejected(client, db, upload_douyin_cookie, fresh_task_manager):
    _override_task_manager(fresh_task_manager)
    try:
        task = _seed_pending_task(db)
        first = client.post(f"/api/v1/analysis/{task.id}/cancel")
        assert first.status_code == 200

        second = client.post(f"/api/v1/analysis/{task.id}/cancel")
        assert second.status_code == 400
        detail = second.json()["detail"].lower()
        assert "terminated" in detail or "cancel" in detail
    finally:
        app.dependency_overrides.pop(get_task_manager, None)


# ---------- F4: 报告 / 标签 / 删除 ----------

def _seed_completed_task_with_report(db) -> tuple[AnalysisTask, ProfileReport]:
    task = AnalysisTask(
        id=str(uuid.uuid4()),
        platform="douyin",
        blogger_url="https://www.douyin.com/user/MS4wLjABAAA_report",
        analysis_level="standard",
        status="completed",
        progress=100,
        current_step="分析完成",
        created_at=_now(),
        updated_at=_now(),
        completed_at=_now(),
    )
    db.add(task)
    db.commit()

    report = ProfileReport(
        id=str(uuid.uuid4()),
        task_id=task.id,
        climate_consumption={
            "climate_zone": {"湿热南方": 42, "干燥北方": 28, "四季分明": 30},
            "summary": "test",
        },
        fragrance_consumption={"price_tier": {"日常平价": 50}, "summary": "test"},
        fashion_fragrance_map={"fashion_style": {"甜美系": 35}, "summary": "test"},
        lifestyle_scenario={"core_interest": {"日常自拍": 28}, "summary": "test"},
        overall_summary="测试整体总结",
        full_report_markdown="## 测试报告\n\n正文...",
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return task, report


def test_get_report_completed(client, db, upload_douyin_cookie):
    task, report = _seed_completed_task_with_report(db)
    resp = client.get(f"/api/v1/analysis/{task.id}/report")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["task_id"] == task.id
    assert "climate_consumption" in data["report"]
    assert data["full_report_markdown"].startswith("##")


def test_get_report_pending_returns_400(client, db, upload_douyin_cookie):
    task = _seed_pending_task(db)
    resp = client.get(f"/api/v1/analysis/{task.id}/report")
    assert resp.status_code == 400
    assert "not generated" in resp.json()["detail"].lower()


def test_get_report_nonexistent(client, db):
    resp = client.get(f"/api/v1/analysis/{uuid.uuid4()}/report")
    assert resp.status_code == 404


def test_get_tags_completed(client, db, upload_douyin_cookie):
    task, _ = _seed_completed_task_with_report(db)
    resp = client.get(f"/api/v1/analysis/{task.id}/tags")
    assert resp.status_code == 200
    dimensions = resp.json()["data"]["dimensions"]
    assert len(dimensions) > 0
    ids = [d["dimension_id"] for d in dimensions]
    assert "climate_consumption" in ids
    # 检查 climate_zone 的互斥标签组（文档 §9.2）
    climate_dim = next(d for d in dimensions if d["dimension_id"] == "climate_consumption")
    climate_zone = next(s for s in climate_dim["sub_dimensions"] if s["sub_id"] == "climate_zone")
    assert climate_zone["is_mutually_exclusive"] is True
    assert climate_zone["max_select"] == 1
    assert all(t["mutually_exclusive_group"] == "climate" for t in climate_zone["tags"])
    # 默认选中比例最高的标签
    assert climate_zone["tags"][0]["is_default_selected"] is True
    assert all(not t["is_default_selected"] for t in climate_zone["tags"][1:])


def test_get_tags_failed_task_returns_400(client, db, upload_douyin_cookie):
    task = AnalysisTask(
        id=str(uuid.uuid4()),
        platform="douyin",
        blogger_url="https://www.douyin.com/user/x",
        analysis_level="standard",
        status="failed",
        progress=30,
        current_step="失败",
        error_message="boom",
        created_at=_now(),
        updated_at=_now(),
    )
    db.add(task)
    db.commit()
    resp = client.get(f"/api/v1/analysis/{task.id}/tags")
    assert resp.status_code == 400
    assert "tags unavailable" in resp.json()["detail"].lower()


def test_delete_completed_task(client, db, upload_douyin_cookie):
    task, _ = _seed_completed_task_with_report(db)
    resp = client.delete(f"/api/v1/analysis/{task.id}")
    assert resp.status_code == 200
    assert resp.json()["message"] == "Task and associated media cleaned up successfully"

    # 再次 GET 应 404
    assert client.get(f"/api/v1/analysis/{task.id}").status_code == 404


def test_delete_mid_run_rejected(client, db, upload_douyin_cookie):
    task = AnalysisTask(
        id=str(uuid.uuid4()),
        platform="douyin",
        blogger_url="https://www.douyin.com/user/x",
        analysis_level="standard",
        status="analyzing",
        progress=55,
        current_step="分析中",
        created_at=_now(),
        updated_at=_now(),
    )
    db.add(task)
    db.commit()
    resp = client.delete(f"/api/v1/analysis/{task.id}")
    assert resp.status_code == 400
    assert "mid-run" in resp.json()["detail"].lower()


# ---------- F3: SSE 进度流 ----------
# 注意：SSE 流式响应在 TestClient (sync) 下跨事件循环会有问题，因此
# 这里使用 httpx.AsyncClient + ASGITransport 在同一事件循环中测试。

import httpx
import pytest_asyncio


@pytest.mark.asyncio
async def test_sse_progress_stream(db, upload_douyin_cookie, fresh_task_manager):
    """通过 task_manager emit 模拟管道进度，验证 SSE 输出格式与契约。"""
    _override_task_manager(fresh_task_manager)
    try:
        task = _seed_pending_task(db)

        # 先提交一个真实任务到 task_manager，让 subscribe 能识别 task_id
        async def pipeline_coro():
            await fresh_task_manager.emit(
                task.id, "progress",
                {"task_id": task.id, "progress": 10, "status": "collecting",
                 "current_step": "采集", "sub_steps": []},
            )
            await asyncio.sleep(0.01)
            await fresh_task_manager.emit(
                task.id, "progress",
                {"task_id": task.id, "progress": 50, "status": "analyzing",
                 "current_step": "分析", "sub_steps": []},
            )
            # complete 事件由 TaskManager.wrapped_coro 保底发送

        await fresh_task_manager.submit(task.id, pipeline_coro())

        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
            async with ac.stream("GET", f"/api/v1/analysis/{task.id}/progress") as resp:
                assert resp.status_code == 200
                assert "text/event-stream" in resp.headers.get("content-type", "")
                chunks: list[str] = []
                async for chunk in resp.aiter_text():
                    chunks.append(chunk)

        text = "".join(chunks)
        events = _parse_sse_events(text)
        types = [e.get("type") for e in events]
        assert "progress" in types
        assert "complete" in types

        progress_events = [e for e in events if e.get("type") == "progress"]
        assert progress_events[0]["data"]["progress"] == 10
        assert progress_events[1]["data"]["progress"] == 50
    finally:
        app.dependency_overrides.pop(get_task_manager, None)


def test_sse_progress_nonexistent_task(client, db):
    resp = client.get(f"/api/v1/analysis/{uuid.uuid4()}/progress")
    assert resp.status_code == 404
