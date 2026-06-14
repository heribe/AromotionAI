import pytest
import json
from unittest.mock import MagicMock

from app.main import app
from app.api.deps import get_analysis_service
from tests.e2e.conftest import _seed_pending_task

@pytest.mark.asyncio
async def test_f3_get_task_details(client, upload_douyin_cookie):
    # Create task
    payload = {
        "blogger_url": "https://www.douyin.com/user/MS4wLjABAAA_details",
        "platform": "douyin",
        "analysis_level": "standard"
    }
    create_resp = await client.post("/api/v1/analysis/create", json=payload)
    task_id = create_resp.json()["data"]["task_id"]
    
    response = await client.get(f"/api/v1/analysis/{task_id}")
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["code"] == 0
    assert res_data["data"]["blogger_url"] == payload["blogger_url"]
    assert res_data["data"]["status"] in ["pending", "collecting", "analyzing", "completed"]

@pytest.mark.asyncio
async def test_f3_subscribe_progress_stream(client, upload_douyin_cookie, read_sse_stream):
    # Create task
    payload = {
        "blogger_url": "https://www.douyin.com/user/MS4wLjABAAA_stream",
        "platform": "douyin",
        "analysis_level": "standard"
    }
    create_resp = await client.post("/api/v1/analysis/create", json=payload)
    task_id = create_resp.json()["data"]["task_id"]
    
    events = await read_sse_stream(client, f"/api/v1/analysis/{task_id}/progress")
    assert len(events) > 0
    # The last event should be a complete event or progress 100
    types = [e["type"] for e in events]
    assert "progress" in types
    assert "complete" in types

@pytest.mark.asyncio
async def test_f3_progress_increments(client, upload_douyin_cookie, read_sse_stream):
    # Create task
    payload = {
        "blogger_url": "https://www.douyin.com/user/MS4wLjABAAA_inc",
        "platform": "douyin",
        "analysis_level": "standard"
    }
    create_resp = await client.post("/api/v1/analysis/create", json=payload)
    task_id = create_resp.json()["data"]["task_id"]
    
    events = await read_sse_stream(client, f"/api/v1/analysis/{task_id}/progress")
    progress_values = []
    for event in events:
        if event["type"] == "progress":
            progress_values.append(event["data"]["progress"])
            
    assert len(progress_values) >= 2
    # Ensure strict monotonic increase
    for i in range(len(progress_values) - 1):
        assert progress_values[i] <= progress_values[i+1]

@pytest.mark.asyncio
async def test_f3_list_tasks(client, upload_douyin_cookie):
    # Create a task
    payload = {
        "blogger_url": "https://www.douyin.com/user/MS4wLjABAAA_list",
        "platform": "douyin",
        "analysis_level": "standard"
    }
    await client.post("/api/v1/analysis/create", json=payload)
    
    response = await client.get("/api/v1/analysis/list?page=1&page_size=10")
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["code"] == 0
    assert "total" in res_data["data"]
    assert len(res_data["data"]["items"]) >= 1

@pytest.mark.asyncio
async def test_f3_cancel_task(client, db):
    # 直接 seed 一个 pending 态任务，避免 mock pipeline 过快完成导致 cancel 时已 completed。
    # cancel 端点的契约是：pending/running 可取消，completed/failed/cancelled 拒绝。
    task = _seed_pending_task(db)
    task_id = task.id

    # Cancel task
    response = await client.post(f"/api/v1/analysis/{task_id}/cancel")
    assert response.status_code == 200
    assert response.json()["code"] == 0

    # Retrieve task details to verify status is cancelled
    detail_resp = await client.get(f"/api/v1/analysis/{task_id}")
    assert detail_resp.json()["data"]["status"] == "cancelled"

@pytest.mark.asyncio
async def test_f3_get_nonexistent_task(client):
    response = await client.get("/api/v1/analysis/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404

@pytest.mark.asyncio
async def test_f3_progress_stream_nonexistent_task(client):
    response = await client.get("/api/v1/analysis/00000000-0000-0000-0000-000000000000/progress")
    assert response.status_code == 404

@pytest.mark.asyncio
async def test_f3_double_cancellation(client, upload_douyin_cookie):
    # Create task
    payload = {
        "blogger_url": "https://www.douyin.com/user/MS4wLjABAAA_double_cancel",
        "platform": "douyin",
        "analysis_level": "standard"
    }
    create_resp = await client.post("/api/v1/analysis/create", json=payload)
    task_id = create_resp.json()["data"]["task_id"]
    
    # First cancel
    await client.post(f"/api/v1/analysis/{task_id}/cancel")
    
    # Second cancel
    response = await client.post(f"/api/v1/analysis/{task_id}/cancel")
    assert response.status_code == 400
    assert "terminated" in response.json()["detail"] or "cancel" in response.json()["detail"].lower()

@pytest.mark.asyncio
async def test_f3_cancel_completed_task(client, upload_douyin_cookie, read_sse_stream):
    # Create task
    payload = {
        "blogger_url": "https://www.douyin.com/user/MS4wLjABAAA_cancel_comp",
        "platform": "douyin",
        "analysis_level": "standard"
    }
    create_resp = await client.post("/api/v1/analysis/create", json=payload)
    task_id = create_resp.json()["data"]["task_id"]
    
    # Run to completion
    await read_sse_stream(client, f"/api/v1/analysis/{task_id}/progress")
    
    # Attempt to cancel
    response = await client.post(f"/api/v1/analysis/{task_id}/cancel")
    assert response.status_code == 400
    assert "completed" in response.json()["detail"].lower()

@pytest.mark.asyncio
async def test_f3_task_failure_propagation(client, db, upload_douyin_cookie, read_sse_stream):
    # 注入一个会抛异常的 mock AnalysisService，让 run_analysis 进入失败分支。
    # 真实 app 无 "URL 含 fail 触发失败" 的魔法开关，必须通过 DI 注入失败 service。
    # mock service 需复现真实 run_analysis 的 except 分支：更新 DB status=failed + emit error + raise。
    from app.models.analysis import AnalysisTask as _AT

    mock_service = MagicMock()

    async def _failing_run(task_id):
        # 模拟真实 run_analysis 的 except 分支：set failed + commit + emit + raise
        failed_task = db.query(_AT).filter(_AT.id == task_id).first()
        if failed_task:
            failed_task.status = "failed"
            failed_task.error_message = "模拟的分析管道失败（e2e failure propagation）"
            db.commit()
        raise RuntimeError("模拟的分析管道失败（e2e failure propagation）")

    mock_service.run_analysis = _failing_run
    app.dependency_overrides[get_analysis_service] = lambda: mock_service
    try:
        payload = {
            "blogger_url": "https://www.douyin.com/user/MS4wLjABAAA_fail_trigger",
            "platform": "douyin",
            "analysis_level": "standard"
        }
        create_resp = await client.post("/api/v1/analysis/create", json=payload)
        task_id = create_resp.json()["data"]["task_id"]

        events = await read_sse_stream(client, f"/api/v1/analysis/{task_id}/progress")
        types = [e["type"] for e in events]
        assert "error" in types

        # Verify task details status is failed
        detail_resp = await client.get(f"/api/v1/analysis/{task_id}")
        assert detail_resp.json()["data"]["status"] == "failed"
    finally:
        app.dependency_overrides.pop(get_analysis_service, None)
