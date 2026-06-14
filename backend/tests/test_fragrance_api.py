"""
Integration tests for Fragrance API endpoints (Part2 §2.1-2.5)。

测试策略：
- 使用 conftest.py 的 client + db fixtures
- 通过 dependency_overrides 注入 mock FragranceService（带 MockEngine）
- 预置 completed AnalysisTask + ProfileReport

R2 三问自检：
1. 契约闭环：每个端点断言 HTTP 状态码、响应 code/data 字段；
   覆盖 §2.1-2.5 可自动测试的路径。
2. 对称性：POST /generate 创建 session，GET /{session_id} 读取，
   POST /regenerate 覆盖；DB function fixture 每 case 重建 schema。
3. 外部时序：mock engine 立即返回，无外部时序问题。
"""

import os
import uuid
import pytest
import datetime

os.environ.setdefault("AROMOTION_TEST_MODE", "mock")

from fastapi.testclient import TestClient

from app.main import app
from app.models.analysis import AnalysisTask
from app.models.profile import ProfileReport
from app.services.fragrance_service import FragranceService
from app.api.v1.fragrance import get_fragrance_service
from tests.test_fragrance_service import (
    MockFragranceEngine,
    _seed_completed_task_with_report,
    _valid_selected_tags,
    _mock_ai_result,
)


def _now():
    return datetime.datetime.now(datetime.timezone.utc)


@pytest.fixture
def mock_engine():
    return MockFragranceEngine()


@pytest.fixture
def override_fragrance_service(db, mock_engine):
    """注入带 MockEngine 的 FragranceService。"""
    def _factory():
        return FragranceService(db, engine=mock_engine)
    app.dependency_overrides[get_fragrance_service] = _factory
    try:
        yield mock_engine
    finally:
        app.dependency_overrides.pop(get_fragrance_service, None)


# ---------- F2: POST /generate ----------

def test_generate_api_success(client, db, override_fragrance_service):
    task, _ = _seed_completed_task_with_report(db)
    payload = {
        "task_id": task.id,
        "selected_tags": _valid_selected_tags(),
        "plan_count": 2,
    }
    resp = client.post("/api/v1/fragrance/generate", json=payload)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["status"] == "completed"
    assert data["session_id"]
    assert len(data["recommendations"]) == 2
    assert data["iceberg_analysis"]["surface"]


def test_generate_task_not_completed_400(client, db, override_fragrance_service):
    task = AnalysisTask(
        id=str(uuid.uuid4()),
        platform="douyin",
        blogger_url="https://www.douyin.com/user/x",
        analysis_level="standard",
        status="pending",
        progress=0,
        current_step="准备",
        created_at=_now(),
        updated_at=_now(),
    )
    db.add(task)
    db.commit()

    payload = {"task_id": task.id, "selected_tags": _valid_selected_tags()}
    resp = client.post("/api/v1/fragrance/generate", json=payload)
    assert resp.status_code == 400


def test_generate_task_not_found_404(client, db, override_fragrance_service):
    payload = {"task_id": str(uuid.uuid4()), "selected_tags": _valid_selected_tags()}
    resp = client.post("/api/v1/fragrance/generate", json=payload)
    assert resp.status_code == 404


def test_generate_invalid_tags_mutex_422(client, db, override_fragrance_service):
    task, _ = _seed_completed_task_with_report(db)
    bad_tags = {"climate_consumption": {"climate_zone": ["湿热南方", "干燥北方"]}}
    payload = {"task_id": task.id, "selected_tags": bad_tags}
    resp = client.post("/api/v1/fragrance/generate", json=payload)
    assert resp.status_code == 422


def test_generate_plan_count_out_of_bounds_422(client, db, override_fragrance_service):
    task, _ = _seed_completed_task_with_report(db)
    payload = {"task_id": task.id, "selected_tags": _valid_selected_tags(), "plan_count": 10}
    resp = client.post("/api/v1/fragrance/generate", json=payload)
    assert resp.status_code == 422


def test_generate_weight_normalization_returns_warnings(client, db, override_fragrance_service):
    task, _ = _seed_completed_task_with_report(db)
    payload = {
        "task_id": task.id,
        "selected_tags": _valid_selected_tags(),
        "blogger_weight": 0.3,
        "audience_weight": 0.4,
    }
    resp = client.post("/api/v1/fragrance/generate", json=payload)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert len(data["warnings"]) == 1


# ---------- F3: GET /{session_id} ----------

def test_get_session_api_success(client, db, override_fragrance_service):
    task, _ = _seed_completed_task_with_report(db)
    gen = client.post("/api/v1/fragrance/generate", json={
        "task_id": task.id, "selected_tags": _valid_selected_tags(), "plan_count": 2
    }).json()["data"]

    resp = client.get(f"/api/v1/fragrance/{gen['session_id']}")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["session_id"] == gen["session_id"]
    assert data["task_id"] == task.id
    assert len(data["recommendations"]) == 2


def test_get_session_not_found_404(client, db, override_fragrance_service):
    resp = client.get(f"/api/v1/fragrance/{uuid.uuid4()}")
    assert resp.status_code == 404


# ---------- F4: POST /{session_id}/chat ----------

def test_chat_api_success(client, db, override_fragrance_service):
    task, _ = _seed_completed_task_with_report(db)
    gen = client.post("/api/v1/fragrance/generate", json={
        "task_id": task.id, "selected_tags": _valid_selected_tags()
    }).json()["data"]

    resp = client.post(f"/api/v1/fragrance/{gen['session_id']}/chat", json={"message": "适合夏天吗？"})
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["reply"]
    assert data["message_id"]


def test_chat_session_not_found_404(client, db, override_fragrance_service):
    resp = client.post(f"/api/v1/fragrance/{uuid.uuid4()}/chat", json={"message": "hi"})
    assert resp.status_code == 404


def test_chat_with_updated_plans(client, db, override_fragrance_service):
    task, _ = _seed_completed_task_with_report(db)
    gen = client.post("/api/v1/fragrance/generate", json={
        "task_id": task.id, "selected_tags": _valid_selected_tags(), "plan_count": 1
    }).json()["data"]

    override_fragrance_service.chat_returns = [
        ("已修改方案一", [{
            "plan_id": "plan_1",
            "name": "修改后方案",
            "category": "木质调",
            "top_notes": [],
            "middle_notes": [],
            "base_notes": [{"name": "沉香", "description": "深", "reason": "改", "changed": True}],
            "recommendation_reason": "理由",
            "fragrance_story": "故事",
        }]),
    ]

    resp = client.post(f"/api/v1/fragrance/{gen['session_id']}/chat", json={"message": "换沉香"})
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["updated_plans"] is not None
    assert data["updated_plans"][0]["plan_id"] == "plan_1"


# ---------- F5: POST /{session_id}/regenerate ----------

def test_regenerate_api_success(client, db, override_fragrance_service):
    task, _ = _seed_completed_task_with_report(db)
    gen = client.post("/api/v1/fragrance/generate", json={
        "task_id": task.id, "selected_tags": _valid_selected_tags(), "plan_count": 1
    }).json()["data"]

    # 先 chat 一轮
    client.post(f"/api/v1/fragrance/{gen['session_id']}/chat", json={"message": "咨询"})

    resp = client.post(f"/api/v1/fragrance/{gen['session_id']}/regenerate", json={"plan_count": 2})
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert len(data["recommendations"]) == 2

    # 验证历史被清空（只剩初始 assistant 消息）
    history = client.get(f"/api/v1/fragrance/{gen['session_id']}/history").json()["data"]
    assert len(history["messages"]) == 1
    assert history["messages"][0]["role"] == "assistant"


def test_regenerate_session_not_found_404(client, db, override_fragrance_service):
    resp = client.post(f"/api/v1/fragrance/{uuid.uuid4()}/regenerate", json={})
    assert resp.status_code == 404


# ---------- F6: GET /{session_id}/history ----------

def test_history_api_success(client, db, override_fragrance_service):
    task, _ = _seed_completed_task_with_report(db)
    gen = client.post("/api/v1/fragrance/generate", json={
        "task_id": task.id, "selected_tags": _valid_selected_tags()
    }).json()["data"]
    client.post(f"/api/v1/fragrance/{gen['session_id']}/chat", json={"message": "咨询"})

    resp = client.get(f"/api/v1/fragrance/{gen['session_id']}/history")
    assert resp.status_code == 200
    messages = resp.json()["data"]["messages"]
    assert len(messages) == 3
    roles = [m["role"] for m in messages]
    assert roles == ["assistant", "user", "assistant"]


def test_history_session_not_found_404(client, db, override_fragrance_service):
    resp = client.get(f"/api/v1/fragrance/{uuid.uuid4()}/history")
    assert resp.status_code == 404
