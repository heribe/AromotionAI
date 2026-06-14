"""
E2E 测试共享 fixtures 与 helpers（M6 改造：指向真实 app/）。

设计要点（R2 三问自检）：
1. 契约闭环：`client` fixture 挂载真实 `app.main:app`，所有 e2e 用例打真实路由；
   通过 `AROMOTION_TEST_MODE=mock` 让 collector/media/analyzer/AI 全走离线分支，
   通过 `dependency_overrides` 注入 mock FragranceEngine，业务逻辑照常跑。
2. 对称性：`db` fixture 每用例 create_all/drop_all；`client` 用 async with
   确保连接释放；`dependency_overrides` 在 fixture teardown 时清理。
3. 外部时序：create 后 run_analysis 异步 submit，SSE 订阅时 task 已落库（analysis.py
   先 commit 后 submit）；通过 `fresh_task_manager` 隔离单例状态。

复用资产：本文件把 `tests/test_analysis_api.py` 与 `tests/test_fragrance_service.py`
里的 helper 统一提炼到一处，避免重复拷贝。
"""

import os
import asyncio
import json
import uuid
import datetime
from typing import Optional
from pathlib import Path

import httpx
import pytest
import pytest_asyncio
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# --- 关键：在 import app 之前设置 mock 模式 ---
# 让 DouyinCollector / MediaProcessor / AI Providers 全部走离线 mock 分支，
# 真实 AnalysisService.run_analysis 可在测试环境离线跑完到 completed。
os.environ.setdefault("AROMOTION_TEST_MODE", "mock")

from app.config import settings

# --- 测试 DB / 目录隔离（与 tests/conftest.py 同构，独立文件避免并发冲突）---
absolute_db_path = settings.BASE_DIR / "data/db/test_e2e_aromotion.db"
absolute_db_url = f"sqlite:///{absolute_db_path}"
absolute_cookie_dir = str(settings.BASE_DIR / "data/test_e2e_cookies")

settings.DATABASE_URL = absolute_db_url
settings.COOKIE_DIR = absolute_cookie_dir

from app.database import Base, get_db
from app.main import app
from app.core.task_manager import TaskManager
from app.api.deps import get_task_manager, get_analysis_service
from app.api.v1.fragrance import get_fragrance_service
from app.models.analysis import AnalysisTask
from app.models.profile import ProfileReport
from app.services.cookie_service import CookieService
from app.services.fragrance_service import FragranceService
from app.engines.base import FragranceEngine


# =====================================================================
# 通用 helpers（从 test_analysis_api.py / test_fragrance_service.py 提炼）
# =====================================================================

def _now():
    """时区感知的 UTC 时间（避免 datetime.utcnow() 弃用警告）。"""
    return datetime.datetime.now(datetime.timezone.utc)


def _seed_pending_task(db) -> AnalysisTask:
    """直接在 DB 构造一个 pending 态任务（绕过 create + pipeline）。"""
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


def _seed_completed_task_with_report(db, suffix: str = "") -> tuple[AnalysisTask, ProfileReport]:
    """直接在 DB 构造一个 completed 任务 + ProfileReport（绕过 pipeline）。

    用于 F4/F5/F6 等依赖已完成任务的用例。合并自 test_analysis_api.py 与
    test_fragrance_service.py 的两份重复实现。报告字段结构是 load-bearing：
    climate_zone / city_tier 等需通过 tags 互斥组校验，overall_summary 供 report 端点读取。
    """
    task = AnalysisTask(
        id=str(uuid.uuid4()),
        platform="douyin",
        blogger_url=f"https://www.douyin.com/user/MS4w_fragrance_test{suffix}",
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
            "climate_zone": {"湿热南方": 60.0, "干燥北方": 40.0},
            "city_tier": {"一线/新一线": 50.0, "二线": 30.0, "三线及以下": 20.0},
            "concentration": "全国分散型（无区域>15%）",
            "summary": "偏向湿热南方气候带",
        },
        fragrance_consumption={
            "price_tier": {"轻奢入门": 50.0, "大众平价": 30.0, "高端沙龙": 20.0},
            "summary": "轻奢消费偏好",
        },
        fashion_fragrance_map={
            "fashion_style": {"甜美系": 40.0, "简约通勤": 35.0, "街头潮流": 25.0},
            "summary": "甜美系穿搭",
        },
        lifestyle_scenario={
            "core_interest": {"日常自拍": 30.0, "美食探店": 25.0},
            "summary": "自拍分享生活方式",
        },
        overall_summary="测试整体画像摘要",
        full_report_markdown="## 测试报告\n\n这是一份 mock 生成的画像报告。",
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return task, report


def _seed_failed_task(db) -> AnalysisTask:
    """直接在 DB 构造一个 failed 任务，用于 F4/F5 的失败分支用例。"""
    task = AnalysisTask(
        id=str(uuid.uuid4()),
        platform="douyin",
        blogger_url="https://www.douyin.com/user/MS4w_failed_task",
        analysis_level="standard",
        status="failed",
        progress=50,
        current_step="分析失败",
        error_message="模拟的分析失败",
        created_at=_now(),
        updated_at=_now(),
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


def _seed_analyzing_task(db) -> AnalysisTask:
    """直接在 DB 构造一个 analyzing 态任务，用于 delete-mid-run 等用例。"""
    task = AnalysisTask(
        id=str(uuid.uuid4()),
        platform="douyin",
        blogger_url="https://www.douyin.com/user/MS4w_analyzing",
        analysis_level="standard",
        status="analyzing",
        progress=40,
        current_step="内容分析",
        created_at=_now(),
        updated_at=_now(),
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


def _valid_selected_tags() -> dict:
    """通过互斥组校验的最小标签集。"""
    return {
        "climate_consumption": {
            "climate_zone": ["湿热南方"],
            "city_tier": ["一线/新一线"],
        },
        "fragrance_consumption": {
            "price_tier": ["轻奢入门"],
        },
    }


def _mock_ai_result(plan_count: int = 2) -> dict:
    """MockFragranceEngine 默认返回值（iceberg + plans + notes 全字段）。"""
    return {
        "iceberg_analysis": {
            "surface": "显性层分析：粉丝偏好花果香调与甜美系穿搭",
            "middle": "情感层分析：追求清新活力与优雅浪漫的情绪表达",
            "deep": "深层分析：渴望通过香气建立精致而独特的个人身份认同",
        },
        "recommendations": [
            {
                "plan_id": f"plan_{i + 1}",
                "name": f"方案 {i + 1}",
                "category": "花果香调",
                "top_notes": [
                    {"name": "佛手柑", "description": "清新柑橘前调", "reason": "活力开场"},
                    {"name": "柠檬", "description": "明亮果香", "reason": "提升清新感"},
                ],
                "middle_notes": [
                    {"name": "玫瑰", "description": "浪漫花香中调", "reason": "优雅主体"},
                ],
                "base_notes": [
                    {"name": "白檀", "description": "温暖木质尾调", "reason": "持久收尾"},
                    {"name": "麝香", "description": "柔和粉香", "reason": "肌肤贴附感"},
                ],
                "recommendation_reason": f"方案 {i + 1} 推荐理由：基于冰山三层分析，"
                "该组合契合粉丝对清新花果香调与优雅气质的双重诉求。",
                "fragrance_story": f"方案 {i + 1} 灵感故事：一场晨光中的花园漫步，"
                "佛手柑的清新与玫瑰的浪漫在白檀的温暖中沉淀，"
                "勾勒出独立而精致的女性形象。",
            }
            for i in range(plan_count)
        ],
    }


class MockFragranceEngine(FragranceEngine):
    """可配置的 mock 引擎：按队列返回 generate / chat 结果。

    合并自 test_fragrance_service.py。e2e 用例可通过 mock_engine fixture 获取实例，
    在测试体内设置 generate_returns / chat_returns / generate_raise / chat_raise
    来精确控制行为。
    """

    def __init__(self):
        self.generate_returns: list[dict] = []
        self.chat_returns: list[tuple[str, Optional[list[dict]]]] = []
        self.generate_call_count = 0
        self.chat_call_count = 0
        self.generate_raise: Optional[Exception] = None
        self.chat_raise: Optional[Exception] = None

    async def generate(self, fused_profile, selected_tags, plan_count=3):
        self.generate_call_count += 1
        if self.generate_raise:
            raise self.generate_raise
        if self.generate_returns:
            return self.generate_returns.pop(0)
        return _mock_ai_result(plan_count)

    async def chat(self, history, current_plans, user_message, selected_tags):
        self.chat_call_count += 1
        if self.chat_raise:
            raise self.chat_raise
        if self.chat_returns:
            return self.chat_returns.pop(0)
        return ("好的，已理解您的需求。", None)


# =====================================================================
# SSE 解析 helper（与真实 SSE 格式兼容）
# 真实 SSE 格式：`event: {type}\ndata: {json}\n\n`（analysis.py:212）
# =====================================================================

async def read_sse_stream_func(client: httpx.AsyncClient, url: str, method: str = "GET",
                               json_payload: dict = None, headers: dict = None):
    """消费 SSE 流直到结束，返回解析后的事件列表。

    对 GET /progress，会读到 complete/error 事件（task_manager.wrapped_coro 保底发 complete）。
    """
    events = []
    req_headers = {"Accept": "text/event-stream"}
    if headers:
        req_headers.update(headers)

    async with client.stream(method, url, json=json_payload, headers=req_headers) as response:
        assert response.status_code == 200, f"SSE stream returned {response.status_code}"
        assert "text/event-stream" in response.headers.get("content-type", "")

        current_event = {}
        async for line in response.aiter_lines():
            line = line.strip()
            if not line:
                if current_event:
                    events.append(current_event)
                    current_event = {}
                continue
            if line.startswith("event:"):
                current_event["type"] = line[len("event:"):].strip()
            elif line.startswith("data:"):
                data_str = line[len("data:"):].strip()
                try:
                    current_event["data"] = json.loads(data_str)
                except json.JSONDecodeError:
                    current_event["data"] = data_str

        if current_event:
            events.append(current_event)

    return events


# =====================================================================
# 失败场景 helper（用于 F3/F4/F5 的 failed task 用例）
# =====================================================================

class _FailingAnalyzer:
    """总是抛异常的 analyzer，用于触发 pipeline 失败。

    注入到 AnalysisService 的 visual_analyzer / comment_analyzer / profile_aggregator
    任一位置，run_analysis 会进入 except 分支，emit error 事件并 set task.status=failed。
    """

    async def analyze(self, *args, **kwargs):
        raise RuntimeError("模拟的分析器失败（e2e failing fixture）")


# =====================================================================
# Pytest fixtures
# =====================================================================

@pytest.fixture(scope="session", autouse=True)
def setup_e2e_env():
    """确保测试目录存在（session 级，只跑一次）。"""
    os.makedirs(os.path.dirname(absolute_db_path), exist_ok=True)
    os.makedirs(absolute_cookie_dir, exist_ok=True)
    yield


@pytest.fixture(scope="function")
def db():
    """函数级隔离 SQLite：每用例 create_all / drop_all。

    与 tests/conftest.py 的 db fixture 同构，但用独立的 test_e2e_*.db 文件
    避免与同步单元测试的 DB 冲突。
    """
    engine = create_engine(absolute_db_url, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def fresh_task_manager():
    """每用例独立的 TaskManager 实例，避免单例事件缓冲跨用例污染。"""
    return TaskManager()


@pytest.fixture(autouse=True)
def _override_di_defaults(db, fresh_task_manager):
    """autouse：默认 override get_db + get_task_manager，确保隔离。

    用例若需更换实例（如 failing pipeline / 自定义 task_manager），
    可在用例内再次 override（dependency_overrides 是 dict，后设覆盖先设）。
    teardown 时统一清理所有 override。
    """
    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_task_manager] = lambda: fresh_task_manager
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def mock_engine():
    """默认的 MockFragranceEngine 实例（用例可配置 generate_returns/chat_returns）。"""
    return MockFragranceEngine()


@pytest.fixture(autouse=True)
def _override_fragrance_service(db, mock_engine):
    """autouse：默认注入带 MockFragranceEngine 的 FragranceService。

    只 mock engine、保留真实 service，让业务逻辑（标签校验/落库/滑窗）照常跑。
    用例可通过获取 mock_engine fixture 在测试体内配置其返回值。
    注意：必须在 _override_di_defaults 之后执行，确保 get_db 已注入。
    """
    def _factory():
        return FragranceService(db, engine=mock_engine)

    app.dependency_overrides[get_fragrance_service] = _factory
    yield
    # 清理由本 fixture 设置的 override（其他 override 由 _override_di_defaults 清理）


@pytest.fixture
def upload_douyin_cookie(db):
    """预置一个有效的抖音 Cookie（通过真实 CookieService 写入测试 DB）。"""
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


@pytest_asyncio.fixture
async def client(db):
    """异步 httpx client 挂载真实 app（ASGITransport），替代旧 stub client。

    修复 httpx 兼容性：旧版用 `httpx.AsyncClient(app=app, ...)` 已废弃，
    新版必须用 `transport=httpx.ASGITransport(app=app)`。
    使用 pytest_asyncio.fixture 而非 pytest.fixture（asyncio_mode=STRICT 要求）。
    """
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac


@pytest.fixture
def read_sse_stream():
    """暴露 read_sse_stream_func 给用例（保留旧 API 签名兼容）。"""
    return read_sse_stream_func


@pytest.fixture
def failing_analysis_service_factory(db, fresh_task_manager):
    """工厂：构造一个会失败的 AnalysisService 实例。

    用法（在用例内）：
        svc = failing_analysis_service_factory()
        app.dependency_overrides[get_analysis_service] = lambda: svc
    """
    from app.services.analysis_service import AnalysisService

    def _make():
        return AnalysisService(
            db,
            fresh_task_manager,
            visual_analyzer=_FailingAnalyzer(),
        )

    return _make
