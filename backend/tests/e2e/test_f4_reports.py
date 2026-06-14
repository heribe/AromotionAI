import pytest
import uuid

@pytest.mark.asyncio
async def test_f4_get_profile_report(client, read_sse_stream):
    # Create task
    payload = {
        "blogger_url": "https://www.douyin.com/user/MS4wLjABAAA_report1",
        "platform": "douyin",
        "analysis_level": "standard"
    }
    create_resp = await client.post("/api/v1/analysis/create", json=payload)
    task_id = create_resp.json()["data"]["task_id"]
    
    # Run to completion
    await read_sse_stream(client, f"/api/v1/analysis/{task_id}/progress")
    
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
async def test_f4_report_markdown_generation(client, read_sse_stream):
    # Create task
    payload = {
        "blogger_url": "https://www.douyin.com/user/MS4wLjABAAA_report2",
        "platform": "douyin",
        "analysis_level": "standard"
    }
    create_resp = await client.post("/api/v1/analysis/create", json=payload)
    task_id = create_resp.json()["data"]["task_id"]
    
    # Run to completion
    await read_sse_stream(client, f"/api/v1/analysis/{task_id}/progress")
    
    response = await client.get(f"/api/v1/analysis/{task_id}/report")
    res_data = response.json()
    markdown = res_data["data"]["full_report_markdown"]
    assert markdown.strip().startswith("##")
    assert "时尚博主A" in markdown

@pytest.mark.asyncio
async def test_f4_get_aggregated_tags(client, read_sse_stream):
    # Create task
    payload = {
        "blogger_url": "https://www.douyin.com/user/MS4wLjABAAA_report3",
        "platform": "douyin",
        "analysis_level": "standard"
    }
    create_resp = await client.post("/api/v1/analysis/create", json=payload)
    task_id = create_resp.json()["data"]["task_id"]
    
    # Run to completion
    await read_sse_stream(client, f"/api/v1/analysis/{task_id}/progress")
    
    response = await client.get(f"/api/v1/analysis/{task_id}/tags")
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["code"] == 0
    dimensions = res_data["data"]["dimensions"]
    assert len(dimensions) > 0
    assert dimensions[0]["dimension_id"] == "climate_consumption"

@pytest.mark.asyncio
async def test_f4_delete_completed_task(client, read_sse_stream):
    # Create task
    payload = {
        "blogger_url": "https://www.douyin.com/user/MS4wLjABAAA_report4",
        "platform": "douyin",
        "analysis_level": "standard"
    }
    create_resp = await client.post("/api/v1/analysis/create", json=payload)
    task_id = create_resp.json()["data"]["task_id"]
    
    # Run to completion
    await read_sse_stream(client, f"/api/v1/analysis/{task_id}/progress")
    
    # Delete
    del_resp = await client.delete(f"/api/v1/analysis/{task_id}")
    assert del_resp.status_code == 200
    
    # Verify task GET returns 404
    get_resp = await client.get(f"/api/v1/analysis/{task_id}")
    assert get_resp.status_code == 404

@pytest.mark.asyncio
async def test_f4_verify_media_cleanup_on_delete(client, read_sse_stream):
    # Create task
    payload = {
        "blogger_url": "https://www.douyin.com/user/MS4wLjABAAA_report5",
        "platform": "douyin",
        "analysis_level": "standard"
    }
    create_resp = await client.post("/api/v1/analysis/create", json=payload)
    task_id = create_resp.json()["data"]["task_id"]
    await read_sse_stream(client, f"/api/v1/analysis/{task_id}/progress")
    
    # Delete task
    del_resp = await client.delete(f"/api/v1/analysis/{task_id}")
    assert del_resp.status_code == 200
    assert del_resp.json()["message"] == "Task and associated media cleaned up successfully"

@pytest.mark.asyncio
async def test_f4_get_report_pending_task(client):
    # Create task, leave as pending
    payload = {
        "blogger_url": "https://www.douyin.com/user/MS4wLjABAAA_report6",
        "platform": "douyin",
        "analysis_level": "standard"
    }
    create_resp = await client.post("/api/v1/analysis/create", json=payload)
    task_id = create_resp.json()["data"]["task_id"]
    
    # Try to query report
    response = await client.get(f"/api/v1/analysis/{task_id}/report")
    assert response.status_code == 400
    assert "report is not generated yet" in response.json()["detail"].lower()

@pytest.mark.asyncio
async def test_f4_get_tags_failed_task(client, read_sse_stream):
    # Create a task that triggers failure using a URL with "fail" in it
    payload = {
        "blogger_url": "https://www.douyin.com/user/MS4wLjABAAA_fail_tags",
        "platform": "douyin",
        "analysis_level": "standard"
    }
    create_resp = await client.post("/api/v1/analysis/create", json=payload)
    task_id = create_resp.json()["data"]["task_id"]
    
    # Run to completion (triggers failure)
    await read_sse_stream(client, f"/api/v1/analysis/{task_id}/progress")
    
    # Verify GET tags returns 400
    response = await client.get(f"/api/v1/analysis/{task_id}/tags")
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
async def test_f4_delete_task_mid_run(client):
    # Create task
    payload = {
        "blogger_url": "https://www.douyin.com/user/MS4wLjABAAA_report7",
        "platform": "douyin",
        "analysis_level": "standard"
    }
    create_resp = await client.post("/api/v1/analysis/create", json=payload)
    task_id = create_resp.json()["data"]["task_id"]
    
    # Manually transition task status to analyzing to simulate mid-run
    from backend.tests.e2e.conftest import tasks as mock_tasks
    mock_tasks[task_id]["status"] = "analyzing"
    
    # Try to delete task
    response = await client.delete(f"/api/v1/analysis/{task_id}")
    assert response.status_code == 400
    assert "cannot delete task mid-run" in response.json()["detail"].lower()
