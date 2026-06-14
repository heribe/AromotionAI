import pytest
import uuid

# Helper to create a completed fragrance session
async def create_completed_session(client, read_sse_stream, suffix=""):
    payload_task = {
        "blogger_url": f"https://www.douyin.com/user/MS4wLjABAAA_chat{suffix}",
        "platform": "douyin",
        "analysis_level": "standard"
    }
    create_resp = await client.post("/api/v1/analysis/create", json=payload_task)
    task_id = create_resp.json()["data"]["task_id"]
    await read_sse_stream(client, f"/api/v1/analysis/{task_id}/progress")
    
    payload_gen = {
        "task_id": task_id,
        "selected_tags": {
            "climate_consumption": {"climate_zone": ["湿热南方"]}
        },
        "plan_count": 3
    }
    gen_resp = await client.post("/api/v1/fragrance/generate", json=payload_gen)
    return gen_resp.json()["data"]["session_id"]

@pytest.mark.asyncio
async def test_f6_post_chat_message(client, read_sse_stream):
    session_id = await create_completed_session(client, read_sse_stream, "1")
    
    payload = {
        "message": "Make the base notes for plan 1 more woody."
    }
    response = await client.post(f"/api/v1/fragrance/{session_id}/chat", json=payload)
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["code"] == 0
    assert "reply" in res_data["data"]
    assert res_data["data"]["updated_plans"] is not None
    assert len(res_data["data"]["updated_plans"]) > 0
    # Verify change
    changed_notes = res_data["data"]["updated_plans"][0]["base_notes"]
    assert any(n.get("changed") for n in changed_notes)

@pytest.mark.asyncio
async def test_f6_retrieve_chat_history(client, read_sse_stream):
    session_id = await create_completed_session(client, read_sse_stream, "2")
    
    # Send a message
    await client.post(
        f"/api/v1/fragrance/{session_id}/chat",
        json={"message": "Make it woody."}
    )
    
    response = await client.get(f"/api/v1/fragrance/{session_id}/history")
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["code"] == 0
    messages = res_data["data"]["messages"]
    # Should contain: initial assistant message, user message, assistant reply
    assert len(messages) >= 3
    assert messages[0]["role"] == "assistant"
    assert messages[1]["role"] == "user"
    assert messages[2]["role"] == "assistant"

@pytest.mark.asyncio
async def test_f6_get_session_details(client, read_sse_stream):
    session_id = await create_completed_session(client, read_sse_stream, "3")
    response = await client.get(f"/api/v1/fragrance/{session_id}")
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["code"] == 0
    assert res_data["data"]["session_id"] == session_id
    assert "recommendations" in res_data["data"]

@pytest.mark.asyncio
async def test_f6_chat_streaming_response(client, read_sse_stream):
    session_id = await create_completed_session(client, read_sse_stream, "4")
    
    # Send chat with Accept header
    payload = {
        "message": "Make it woody."
    }
    events = await read_sse_stream(
        client,
        f"/api/v1/fragrance/{session_id}/chat",
        method="POST",
        json_payload=payload,
        headers={"Accept": "text/event-stream"}
    )
    assert len(events) > 0
    # The last chunk should contain the final JSON payload
    last_event = events[-1]
    # In conftest, the final data has no event type (defaults to data only) or we check value
    assert "reply" in last_event["data"]
    assert last_event["data"]["updated_plans"] is not None

@pytest.mark.asyncio
async def test_f6_regenerate_session(client, read_sse_stream):
    session_id = await create_completed_session(client, read_sse_stream, "5")
    
    payload = {
        "selected_tags": {
            "fashion_fragrance_map": {"fashion_style": ["古典系"]}
        },
        "plan_count": 2
    }
    response = await client.post(f"/api/v1/fragrance/{session_id}/regenerate", json=payload)
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["code"] == 0
    
    # Retrieve history to ensure it was cleared and reset to initial regen message
    history_resp = await client.get(f"/api/v1/fragrance/{session_id}/history")
    messages = history_resp.json()["data"]["messages"]
    assert len(messages) == 1
    assert "重新选择" in messages[0]["content"]

@pytest.mark.asyncio
async def test_f6_chat_nonexistent_session(client):
    rand_uuid = str(uuid.uuid4())
    payload = {"message": "hello"}
    response = await client.post(f"/api/v1/fragrance/{rand_uuid}/chat", json=payload)
    assert response.status_code == 404

@pytest.mark.asyncio
async def test_f6_chat_empty_message(client, read_sse_stream):
    session_id = await create_completed_session(client, read_sse_stream, "6")
    payload = {"message": "   "}
    response = await client.post(f"/api/v1/fragrance/{session_id}/chat", json=payload)
    assert response.status_code == 400

@pytest.mark.asyncio
async def test_f6_chat_malformed_json_reply(client, read_sse_stream):
    session_id = await create_completed_session(client, read_sse_stream, "7")
    payload = {"message": "malformed_json"}
    response = await client.post(f"/api/v1/fragrance/{session_id}/chat", json=payload)
    # conftest needs to raise 502 for this
    assert response.status_code == 502

@pytest.mark.asyncio
async def test_f6_get_nonexistent_session(client):
    rand_uuid = str(uuid.uuid4())
    response = await client.get(f"/api/v1/fragrance/{rand_uuid}")
    assert response.status_code == 404

@pytest.mark.asyncio
async def test_f6_get_nonexistent_session_history(client):
    rand_uuid = str(uuid.uuid4())
    response = await client.get(f"/api/v1/fragrance/{rand_uuid}/history")
    assert response.status_code == 404
