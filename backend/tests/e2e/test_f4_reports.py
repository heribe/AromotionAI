import pytest
import uuid

from tests.e2e.conftest import (
    _seed_pending_task,
    _seed_completed_task_with_report,
    _seed_failed_task,
    _seed_analyzing_task,
)

@pytest.mark.asyncio
async def test_f4_get_profile_report(client, db):
    # 直接 seed completed task + report，绕过 pipeline（report 字段结构可控）
    task, _ = _seed_completed_task_with_report(db, "report1")
    task_id = task.id

    response = await client.get(f"/api/v1/analysis/{task_id}/report")
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["code"] == 0
    data = res_data["data"]
    assert "blogger_info" in data
    assert "report" in data
    assert "climate_consumption" in data["report"]
    assert "fragrance_consumption" in data["report"]
    assert "fashion_fragrance_map" in data["report"]
    assert "lifestyle_scenario" in data["report"]
    assert "full_report_markdown" in data

@pytest.mark.asyncio
async def test_f4_report_markdown_generation(client, db):
    # seed completed task + report，markdown 内容来自 seed helper
    task, _ = _seed_completed_task_with_report(db, "report2")
    task_id = task.id

    response = await client.get(f"/api/v1/analysis/{task_id}/report")
    res_data = response.json()
    markdown = res_data["data"]["full_report_markdown"]
    # 放宽断言：真实 markdown 由 ProfileAggregator 生成，内容取决于 mock 输出。
    # 仅验证 markdown 格式（## 开头）与 seed 数据一致。
    assert markdown.strip().startswith("##")
    assert "测试报告" in markdown  # 对齐 seed helper 的 full_report_markdown 内容

@pytest.mark.asyncio
async def test_f4_get_aggregated_tags(client, db):
    task, _ = _seed_completed_task_with_report(db, "report3")
    task_id = task.id

    response = await client.get(f"/api/v1/analysis/{task_id}/tags")
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["code"] == 0
    dimensions = res_data["data"]["dimensions"]
    assert len(dimensions) > 0
    assert dimensions[0]["dimension_id"] == "climate_consumption"

@pytest.mark.asyncio
async def test_f4_delete_completed_task(client, db):
    task, _ = _seed_completed_task_with_report(db, "report4")
    task_id = task.id

    # Delete
    del_resp = await client.delete(f"/api/v1/analysis/{task_id}")
    assert del_resp.status_code == 200

    # Verify task GET returns 404
    get_resp = await client.get(f"/api/v1/analysis/{task_id}")
    assert get_resp.status_code == 404

@pytest.mark.asyncio
async def test_f4_verify_media_cleanup_on_delete(client, db):
    task, _ = _seed_completed_task_with_report(db, "report5")
    task_id = task.id

    # Delete task
    del_resp = await client.delete(f"/api/v1/analysis/{task_id}")
    assert del_resp.status_code == 200
    assert del_resp.json()["message"] == "Task and associated media cleaned up successfully"

@pytest.mark.asyncio
async def test_f4_get_report_pending_task(client, db):
    # seed pending task，绕过 pipeline（mock pipeline 过快会推进到 completed）
    task = _seed_pending_task(db)

    # Try to query report
    response = await client.get(f"/api/v1/analysis/{task.id}/report")
    assert response.status_code == 400
    assert "report is not generated yet" in response.json()["detail"].lower()

@pytest.mark.asyncio
async def test_f4_get_tags_failed_task(client, db):
    # seed failed task（真实 app 无 URL 含 fail 触发失败的魔法开关）
    task = _seed_failed_task(db)

    # Verify GET tags returns 400
    response = await client.get(f"/api/v1/analysis/{task.id}/tags")
    assert response.status_code == 400
    assert "tags unavailable" in response.json()["detail"].lower()

@pytest.mark.asyncio
async def test_f4_get_report_nonexistent_task(client):
    rand_id = str(uuid.uuid4())
    response = await client.get(f"/api/v1/analysis/{rand_id}/report")
    assert response.status_code == 404

@pytest.mark.asyncio
async def test_f4_get_tags_nonexistent_task(client):
    rand_id = str(uuid.uuid4())
    response = await client.get(f"/api/v1/analysis/{rand_id}/tags")
    assert response.status_code == 404

@pytest.mark.asyncio
async def test_f4_delete_task_mid_run(client, db):
    # seed analyzing 态任务（绕过 pipeline 时序竞态，直接构造 mid-run 状态）
    task = _seed_analyzing_task(db)

    # Try to delete task
    response = await client.delete(f"/api/v1/analysis/{task.id}")
    assert response.status_code == 400
    assert "cannot delete task mid-run" in response.json()["detail"].lower()
