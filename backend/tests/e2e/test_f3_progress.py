import pytest
import json

@pytest.mark.asyncio
async def test_f3_get_task_details(client):
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
async def test_f3_subscribe_progress_stream(client, read_sse_stream):
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
async def test_f3_progress_increments(client, read_sse_stream):
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
async def test_f3_list_tasks(client):
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
async def test_f3_cancel_task(client):
    # Create task
    payload = {
        "blogger_url": "https://www.douyin.com/user/MS4wLjABAAA_cancel",
        "platform": "douyin",
        "analysis_level": "standard"
    }
    create_resp = await client.post("/api/v1/analysis/create", json=payload)
    task_id = create_resp.json()["data"]["task_id"]
    
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
async def test_f3_double_cancellation(client):
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
async def test_f3_cancel_completed_task(client, read_sse_stream):
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
async def test_f3_task_failure_propagation(client, read_sse_stream):
    # Create a task that triggers failure using a URL with "fail" in it
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
