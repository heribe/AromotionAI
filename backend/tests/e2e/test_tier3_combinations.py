import pytest
import asyncio
import json

@pytest.mark.asyncio
async def test_t3_cookie_deletion_mid_task(client):
    # Ensure cookie exists
    await client.post(
        "/api/v1/cookies/upload",
        data={"platform": "douyin"},
        files={"file": ("cookie.json", b'[{"name":"sessionid","value":"1"}]')}
    )
    
    # Create task
    payload = {
        "blogger_url": "https://www.douyin.com/user/MS4wLjABAAA_t3_cookie",
        "platform": "douyin",
        "analysis_level": "standard"
    }
    create_resp = await client.post("/api/v1/analysis/create", json=payload)
    task_id = create_resp.json()["data"]["task_id"]
    
    # Subscribe and delete cookie mid-run
    events = []
    async with client.stream("GET", f"/api/v1/analysis/{task_id}/progress") as response:
        assert response.status_code == 200
        async for line in response.aiter_lines():
            line = line.strip()
            if line.startswith("data:"):
                events.append(line)
                # Delete the cookie after receiving the first progress update
                await client.delete("/api/v1/cookies/douyin")
                
    # Verify we received an error event
    error_event_found = False
    for e in events:
        if "CookieExpiredError" in e or "cookie missing" in e.lower() or "error" in e.lower():
            error_event_found = True
            break
    assert error_event_found
    
    # Verify task status is failed
    task_resp = await client.get(f"/api/v1/analysis/{task_id}")
    assert task_resp.json()["data"]["status"] == "failed"

@pytest.mark.asyncio
async def test_t3_task_deletion_impact_on_sse(client):
    # Create task
    payload = {
        "blogger_url": "https://www.douyin.com/user/MS4wLjABAAA_t3_del",
        "platform": "douyin",
        "analysis_level": "standard"
    }
    create_resp = await client.post("/api/v1/analysis/create", json=payload)
    task_id = create_resp.json()["data"]["task_id"]
    
    # Subscribe and delete task mid-run
    events = []
    async with client.stream("GET", f"/api/v1/analysis/{task_id}/progress") as response:
        assert response.status_code == 200
        async for line in response.aiter_lines():
            line = line.strip()
            if line.startswith("data:"):
                events.append(line)
                # Delete task
                await client.delete(f"/api/v1/analysis/{task_id}")
                
    # Verify stream terminated early due to task deletion
    # Subsequent details query should return 404
    detail_resp = await client.get(f"/api/v1/analysis/{task_id}")
    assert detail_resp.status_code == 404

@pytest.mark.asyncio
async def test_t3_tag_selection_to_recommendation_flow(client, read_sse_stream):
    # 1. Create and complete task
    payload = {
        "blogger_url": "https://www.douyin.com/user/MS4wLjABAAA_t3_tags",
        "platform": "douyin",
        "analysis_level": "standard"
    }
    create_resp = await client.post("/api/v1/analysis/create", json=payload)
    task_id = create_resp.json()["data"]["task_id"]
    await read_sse_stream(client, f"/api/v1/analysis/{task_id}/progress")
    
    # 2. Retrieve tags
    tags_resp = await client.get(f"/api/v1/analysis/{task_id}/tags")
    dimensions = tags_resp.json()["data"]["dimensions"]
    
    # Extract subset of tags
    selected_tags = {
        "climate_consumption": {
            "climate_zone": [dimensions[0]["sub_dimensions"][0]["tags"][0]["name"]]
        }
    }
    
    # 3. Generate fragrance
    payload_gen = {
        "task_id": task_id,
        "selected_tags": selected_tags,
        "plan_count": 3
    }
    gen_resp = await client.post("/api/v1/fragrance/generate", json=payload_gen)
    assert gen_resp.status_code == 200
    session_id = gen_resp.json()["data"]["session_id"]
    
    # Verify session is associated with task_id
    sess_detail = await client.get(f"/api/v1/fragrance/{session_id}")
    assert sess_detail.json()["data"]["task_id"] == task_id

@pytest.mark.asyncio
async def test_t3_chat_history_updates_on_recalculations(client, read_sse_stream):
    # Create task & session
    payload_task = {
        "blogger_url": "https://www.douyin.com/user/MS4wLjABAAA_t3_recalc",
        "platform": "douyin",
        "analysis_level": "standard"
    }
    create_resp = await client.post("/api/v1/analysis/create", json=payload_task)
    task_id = create_resp.json()["data"]["task_id"]
    await read_sse_stream(client, f"/api/v1/analysis/{task_id}/progress")
    
    payload_gen = {
        "task_id": task_id,
        "selected_tags": {"climate_consumption": {"climate_zone": ["湿热南方"]}},
        "plan_count": 3
    }
    gen_resp = await client.post("/api/v1/fragrance/generate", json=payload_gen)
    session_id = gen_resp.json()["data"]["session_id"]
    
    # Send feedback chat
    await client.post(
        f"/api/v1/fragrance/{session_id}/chat",
        json={"message": "Make it woody."}
    )
    
    # Trigger regeneration
    payload_regen = {
        "selected_tags": {"fashion_fragrance_map": {"fashion_style": ["古典系"]}},
        "plan_count": 2
    }
    regen_resp = await client.post(f"/api/v1/fragrance/{session_id}/regenerate", json=payload_regen)
    assert regen_resp.status_code == 200
    
    # Get history and verify the state
    hist_resp = await client.get(f"/api/v1/fragrance/{session_id}/history")
    messages = hist_resp.json()["data"]["messages"]
    assert len(messages) == 1
    assert "重新选择" in messages[0]["content"]

@pytest.mark.asyncio
async def test_t3_ai_config_updates_modifying_model_targets(client, read_sse_stream):
    # Create completed task
    payload_task = {
        "blogger_url": "https://www.douyin.com/user/MS4wLjABAAA_t3_ai",
        "platform": "douyin",
        "analysis_level": "standard"
    }
    create_resp = await client.post("/api/v1/analysis/create", json=payload_task)
    task_id = create_resp.json()["data"]["task_id"]
    await read_sse_stream(client, f"/api/v1/analysis/{task_id}/progress")
    
    # Update AI Provider config
    payload_route = {
        "slot": "fragrance_reasoning",
        "model": "deepseek-coder"
    }
    route_resp = await client.put(
        "/api/v1/config/ai-providers/deepseek",
        json=payload_route,
        headers={"Authorization": "Bearer admin_token"}
    )
    assert route_resp.status_code == 200
    
    # Generate recommendations
    payload_gen = {
        "task_id": task_id,
        "selected_tags": {"climate_consumption": {"climate_zone": ["湿热南方"]}},
        "plan_count": 3
    }
    gen_resp = await client.post("/api/v1/fragrance/generate", json=payload_gen)
    assert gen_resp.status_code == 200
    
    # Verify routing updated in state
    from backend.tests.e2e.conftest import ai_routing
    assert ai_routing["fragrance_reasoning"]["provider"] == "deepseek"
    assert ai_routing["fragrance_reasoning"]["model"] == "deepseek-coder"

@pytest.mark.asyncio
async def test_t3_task_cascade_deletion(client, read_sse_stream):
    # 1. Create and complete task
    payload_task = {
        "blogger_url": "https://www.douyin.com/user/MS4wLjABAAA_t3_cascade",
        "platform": "douyin",
        "analysis_level": "standard"
    }
    create_resp = await client.post("/api/v1/analysis/create", json=payload_task)
    task_id = create_resp.json()["data"]["task_id"]
    await read_sse_stream(client, f"/api/v1/analysis/{task_id}/progress")
    
    # 2. Generate recommendation
    payload_gen = {
        "task_id": task_id,
        "selected_tags": {"climate_consumption": {"climate_zone": ["湿热南方"]}},
        "plan_count": 3
    }
    gen_resp = await client.post("/api/v1/fragrance/generate", json=payload_gen)
    session_id = gen_resp.json()["data"]["session_id"]
    
    # 3. Add chat message
    await client.post(
        f"/api/v1/fragrance/{session_id}/chat",
        json={"message": "Make it woody."}
    )
    
    # 4. Delete the task
    del_resp = await client.delete(f"/api/v1/analysis/{task_id}")
    assert del_resp.status_code == 200
    
    # 5. Check cascade deletes: GET task, report, tags, session, history -> 404
    assert (await client.get(f"/api/v1/analysis/{task_id}")).status_code == 404
    assert (await client.get(f"/api/v1/analysis/{task_id}/report")).status_code == 404
    assert (await client.get(f"/api/v1/analysis/{task_id}/tags")).status_code == 404
    assert (await client.get(f"/api/v1/fragrance/{session_id}")).status_code == 404
    assert (await client.get(f"/api/v1/fragrance/{session_id}/history")).status_code == 404

@pytest.mark.asyncio
async def test_t3_multiple_concurrent_tasks_single_cookie(client, read_sse_stream):
    # Upload cookie
    await client.post(
        "/api/v1/cookies/upload",
        data={"platform": "douyin"},
        files={"file": ("cookie.json", b'[{"name":"sessionid","value":"1"}]')}
    )
    
    # Create 3 tasks concurrently
    payloads = [
        {
            "blogger_url": f"https://www.douyin.com/user/MS4wLjABAAA_t3_concurrent_{i}",
            "platform": "douyin",
            "analysis_level": "standard"
        }
        for i in range(3)
    ]
    
    create_responses = await asyncio.gather(*[
        client.post("/api/v1/analysis/create", json=p) for p in payloads
    ])
    
    task_ids = [r.json()["data"]["task_id"] for r in create_responses]
    
    # Read SSE progress streams concurrently
    stream_tasks = [
        read_sse_stream(client, f"/api/v1/analysis/{tid}/progress")
        for tid in task_ids
    ]
    
    results = await asyncio.gather(*stream_tasks)
    
    # Ensure all tasks finished successfully (last event contains complete)
    for tid, events in zip(task_ids, results):
        assert any(e["type"] == "complete" for e in events)
        
        # Verify task is marked completed
        details = await client.get(f"/api/v1/analysis/{tid}")
        assert details.json()["data"]["status"] == "completed"
