import pytest
import uuid

# Helper to create a completed task
async def create_completed_task(client, read_sse_stream, suffix=""):
    payload = {
        "blogger_url": f"https://www.douyin.com/user/MS4wLjABAAA_fragrance{suffix}",
        "platform": "douyin",
        "analysis_level": "standard"
    }
    create_resp = await client.post("/api/v1/analysis/create", json=payload)
    task_id = create_resp.json()["data"]["task_id"]
    await read_sse_stream(client, f"/api/v1/analysis/{task_id}/progress")
    return task_id

@pytest.mark.asyncio
async def test_f5_generate_fragrance(client, read_sse_stream):
    task_id = await create_completed_task(client, read_sse_stream, "1")
    payload = {
        "task_id": task_id,
        "selected_tags": {
            "climate_consumption": {
                "climate_zone": ["湿热南方"]
            }
        },
        "plan_count": 3
    }
    response = await client.post("/api/v1/fragrance/generate", json=payload)
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["code"] == 0
    assert "session_id" in res_data["data"]
    assert res_data["data"]["status"] == "completed"
    assert len(res_data["data"]["recommendations"]) == 3

@pytest.mark.asyncio
async def test_f5_plan_count_validation(client, read_sse_stream):
    task_id = await create_completed_task(client, read_sse_stream, "2")
    payload = {
        "task_id": task_id,
        "selected_tags": {
            "climate_consumption": {
                "climate_zone": ["湿热南方"]
            }
        },
        "plan_count": 2
    }
    response = await client.post("/api/v1/fragrance/generate", json=payload)
    assert response.status_code == 200
    res_data = response.json()
    assert len(res_data["data"]["recommendations"]) == 2

@pytest.mark.asyncio
async def test_f5_iceberg_structure_verification(client, read_sse_stream):
    task_id = await create_completed_task(client, read_sse_stream, "3")
    payload = {
        "task_id": task_id,
        "selected_tags": {
            "climate_consumption": {
                "climate_zone": ["湿热南方"]
            }
        },
        "plan_count": 1
    }
    response = await client.post("/api/v1/fragrance/generate", json=payload)
    session_id = response.json()["data"]["session_id"]
    
    # Get session details
    detail_resp = await client.get(f"/api/v1/fragrance/{session_id}")
    assert detail_resp.status_code == 200
    session_data = detail_resp.json()["data"]
    assert "iceberg_analysis" in session_data
    iceberg = session_data["iceberg_analysis"]
    assert "surface" in iceberg and len(iceberg["surface"]) > 0
    assert "middle" in iceberg and len(iceberg["middle"]) > 0
    assert "deep" in iceberg and len(iceberg["deep"]) > 0

@pytest.mark.asyncio
async def test_f5_notes_fields_verification(client, read_sse_stream):
    task_id = await create_completed_task(client, read_sse_stream, "4")
    payload = {
        "task_id": task_id,
        "selected_tags": {
            "climate_consumption": {
                "climate_zone": ["湿热南方"]
            }
        },
        "plan_count": 1
    }
    response = await client.post("/api/v1/fragrance/generate", json=payload)
    plan = response.json()["data"]["recommendations"][0]
    
    for note_group in ["top_notes", "middle_notes", "base_notes"]:
        assert note_group in plan
        for note in plan[note_group]:
            assert "name" in note and len(note["name"]) > 0
            assert "description" in note and len(note["description"]) > 0
            assert "reason" in note and len(note["reason"]) > 0

@pytest.mark.asyncio
async def test_f5_story_and_reason_generation(client, read_sse_stream):
    task_id = await create_completed_task(client, read_sse_stream, "5")
    payload = {
        "task_id": task_id,
        "selected_tags": {
            "climate_consumption": {
                "climate_zone": ["湿热南方"]
            }
        },
        "plan_count": 1
    }
    response = await client.post("/api/v1/fragrance/generate", json=payload)
    plan = response.json()["data"]["recommendations"][0]
    assert "recommendation_reason" in plan and len(plan["recommendation_reason"]) > 50
    assert "fragrance_story" in plan and len(plan["fragrance_story"]) > 50

@pytest.mark.asyncio
async def test_f5_generate_nonexistent_task(client):
    rand_uuid = str(uuid.uuid4())
    payload = {
        "task_id": rand_uuid,
        "selected_tags": {"climate_consumption": {"climate_zone": ["湿热南方"]}}
    }
    response = await client.post("/api/v1/fragrance/generate", json=payload)
    assert response.status_code == 404

@pytest.mark.asyncio
async def test_f5_generate_failed_task(client, read_sse_stream):
    # Create a task that triggers failure
    payload = {
        "blogger_url": "https://www.douyin.com/user/MS4wLjABAAA_fail_frag",
        "platform": "douyin",
        "analysis_level": "standard"
    }
    create_resp = await client.post("/api/v1/analysis/create", json=payload)
    task_id = create_resp.json()["data"]["task_id"]
    await read_sse_stream(client, f"/api/v1/analysis/{task_id}/progress")
    
    # Try generating fragrance for failed task
    payload_gen = {
        "task_id": task_id,
        "selected_tags": {"climate_consumption": {"climate_zone": ["湿热南方"]}}
    }
    response = await client.post("/api/v1/fragrance/generate", json=payload_gen)
    assert response.status_code == 400
    assert "failed" in response.json()["detail"].lower()

@pytest.mark.asyncio
async def test_f5_generate_empty_tags(client, read_sse_stream):
    task_id = await create_completed_task(client, read_sse_stream, "6")
    payload = {
        "task_id": task_id,
        "selected_tags": {}
    }
    response = await client.post("/api/v1/fragrance/generate", json=payload)
    assert response.status_code == 400

@pytest.mark.asyncio
async def test_f5_generate_invalid_tags_structure(client, read_sse_stream):
    task_id = await create_completed_task(client, read_sse_stream, "7")
    payload = {
        "task_id": task_id,
        "selected_tags": "not-a-dict"
    }
    response = await client.post("/api/v1/fragrance/generate", json=payload)
    assert response.status_code == 422

@pytest.mark.asyncio
async def test_f5_generate_invalid_plan_count(client, read_sse_stream):
    task_id = await create_completed_task(client, read_sse_stream, "8")
    payload = {
        "task_id": task_id,
        "selected_tags": {"climate_consumption": {"climate_zone": ["湿热南方"]}},
        "plan_count": 0  # Invalid < 1
    }
    response = await client.post("/api/v1/fragrance/generate", json=payload)
    assert response.status_code == 422
    
    payload["plan_count"] = 11  # Invalid > 10
    response = await client.post("/api/v1/fragrance/generate", json=payload)
    assert response.status_code == 422
