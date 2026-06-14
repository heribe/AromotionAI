import pytest
import asyncio
import json

@pytest.mark.asyncio
async def test_scenario_1_happy_path(client, read_sse_stream):
    # Step 1: Upload a valid Douyin cookie. Check status.
    upload_resp = await client.post(
        "/api/v1/cookies/upload",
        data={"platform": "douyin"},
        files={"file": ("cookie.json", b'[{"name":"sessionid","value":"active"}]')}
    )
    assert upload_resp.status_code == 200
    
    status_resp = await client.get("/api/v1/cookies/status?platform=douyin")
    assert status_resp.json()["data"]["cookies"][0]["is_valid"] is True

    # Step 2: Submit a task for a Douyin blogger. Get task_id.
    create_resp = await client.post(
        "/api/v1/analysis/create",
        json={
            "blogger_url": "https://www.douyin.com/user/MS4wLjABAAA_happy",
            "platform": "douyin",
            "analysis_level": "standard"
        }
    )
    assert create_resp.status_code == 200
    task_id = create_resp.json()["data"]["task_id"]

    # Step 3: Open SSE connection. Read events until complete.
    events = await read_sse_stream(client, f"/api/v1/analysis/{task_id}/progress")
    assert any(e["type"] == "complete" for e in events)

    # Step 4: Fetch report and verify. Fetch tags.
    report_resp = await client.get(f"/api/v1/analysis/{task_id}/report")
    assert report_resp.status_code == 200
    assert "climate_consumption" in report_resp.json()["data"]["report"]

    tags_resp = await client.get(f"/api/v1/analysis/{task_id}/tags")
    assert tags_resp.status_code == 200
    dimensions = tags_resp.json()["data"]["dimensions"]

    # Step 5: Select tags and generate fragrance recommendations.
    selected_tags = {
        "climate_consumption": {
            "climate_zone": [dimensions[0]["sub_dimensions"][0]["tags"][0]["name"]]
        }
    }
    gen_resp = await client.post(
        "/api/v1/fragrance/generate",
        json={
            "task_id": task_id,
            "selected_tags": selected_tags,
            "plan_count": 3
        }
    )
    assert gen_resp.status_code == 200
    session_id = gen_resp.json()["data"]["session_id"]
    assert len(gen_resp.json()["data"]["recommendations"]) == 3

    # Step 6: Send feedback: "Make base notes for plan 1 more woody".
    chat_resp = await client.post(
        f"/api/v1/fragrance/{session_id}/chat",
        json={"message": "Make the base notes for plan 1 more woody."}
    )
    assert chat_resp.status_code == 200
    chat_data = chat_resp.json()["data"]
    assert chat_data["updated_plans"] is not None
    # Verify plan 1 base notes have changed flag
    assert any(note.get("changed") for note in chat_data["updated_plans"][0]["base_notes"])

    # Step 7: Fetch history and verify turns.
    hist_resp = await client.get(f"/api/v1/fragrance/{session_id}/history")
    messages = hist_resp.json()["data"]["messages"]
    assert len(messages) == 3
    assert messages[1]["role"] == "user"
    assert messages[2]["role"] == "assistant"

@pytest.mark.asyncio
async def test_scenario_2_cookie_lifecycle(client):
    # Step 1: Upload cookie. Start task.
    await client.post(
        "/api/v1/cookies/upload",
        data={"platform": "douyin"},
        files={"file": ("cookie.json", b'[{"name":"sessionid","value":"v1"}]')}
    )
    
    create_resp = await client.post(
        "/api/v1/analysis/create",
        json={
            "blogger_url": "https://www.douyin.com/user/MS4wLjABAAA_lifecycle",
            "platform": "douyin",
            "analysis_level": "standard"
        }
    )
    task_id = create_resp.json()["data"]["task_id"]

    # Step 2 & 3: Simulate cookie deletion mid-run (overriding with invalid cookie or deleting it).
    # We will read progress events, and delete the cookie after the first progress event.
    events = []
    async with client.stream("GET", f"/api/v1/analysis/{task_id}/progress") as response:
        async for line in response.aiter_lines():
            line = line.strip()
            if line.startswith("data:"):
                events.append(line)
                # Delete the cookie
                await client.delete("/api/v1/cookies/douyin")

    # Verify task failed
    task_detail = await client.get(f"/api/v1/analysis/{task_id}")
    assert task_detail.json()["data"]["status"] == "failed"

    # Step 4 & 5: Upload valid cookie and retry task creation.
    await client.post(
        "/api/v1/cookies/upload",
        data={"platform": "douyin"},
        files={"file": ("cookie.json", b'[{"name":"sessionid","value":"v2"}]')}
    )
    
    create_resp_2 = await client.post(
        "/api/v1/analysis/create",
        json={
            "blogger_url": "https://www.douyin.com/user/MS4wLjABAAA_lifecycle",
            "platform": "douyin",
            "analysis_level": "standard"
        }
    )
    task_id_2 = create_resp_2.json()["data"]["task_id"]

    # Step 6: Verify it completes and generates reports/tags.
    async with client.stream("GET", f"/api/v1/analysis/{task_id_2}/progress") as response:
        async for line in response.aiter_lines():
            pass # read till the end
            
    task_detail_2 = await client.get(f"/api/v1/analysis/{task_id_2}")
    assert task_detail_2.json()["data"]["status"] == "completed"

    report_resp = await client.get(f"/api/v1/analysis/{task_id_2}/report")
    assert report_resp.status_code == 200
    tags_resp = await client.get(f"/api/v1/analysis/{task_id_2}/tags")
    assert tags_resp.status_code == 200

    # Step 7: Clean up by deleting the cookie and checking status returns invalid/inactive.
    await client.delete("/api/v1/cookies/douyin")
    status_resp = await client.get("/api/v1/cookies/status?platform=douyin")
    assert status_resp.json()["data"]["cookies"][0]["is_valid"] is False

@pytest.mark.asyncio
async def test_scenario_3_custom_config_tuning(client, read_sse_stream):
    # Step 1: Create a task with customized boundaries:
    custom_config = {
        "post_selection": {
            "top_count": 10,
            "recent_count": 5,
            "sort_by": "comments"
        },
        "comment": {
            "per_post_count": 20,
            "sort_by": "hot"
        },
        "commenter_analysis": {
            "enabled": True,
            "max_count": 20,
            "analyze_posts": True,
            "posts_per_commenter": 3,
            "analyze_post_content": True,
            "analyze_video": False
        },
        "visual_analysis": {
            "cover_analysis": True,
            "video_frame_analysis": True,
            "frames_per_video": 3
        }
    }
    
    # Ensure cookie is uploaded
    await client.post(
        "/api/v1/cookies/upload",
        data={"platform": "douyin"},
        files={"file": ("cookie.json", b'[{"name":"sessionid","value":"active"}]')}
    )
    
    create_resp = await client.post(
        "/api/v1/analysis/create",
        json={
            "blogger_url": "https://www.douyin.com/user/MS4wLjABAAA_custom_tuning",
            "platform": "douyin",
            "analysis_level": "custom",
            "custom_config": custom_config
        }
    )
    assert create_resp.status_code == 200
    task_id = create_resp.json()["data"]["task_id"]

    # Step 2: Monitor task execution via SSE and verify steps.
    events = await read_sse_stream(client, f"/api/v1/analysis/{task_id}/progress")
    assert any(e["type"] == "complete" for e in events)

    # Step 3 & 4: Retrieve task and verify custom configs.
    task_detail = await client.get(f"/api/v1/analysis/{task_id}")
    task_data = task_detail.json()["data"]
    assert task_data["custom_config"]["post_selection"]["top_count"] == 10
    assert task_data["custom_config"]["post_selection"]["recent_count"] == 5
    assert task_data["custom_config"]["visual_analysis"]["frames_per_video"] == 3

    # Step 5: Generate recommendation.
    gen_resp = await client.post(
        "/api/v1/fragrance/generate",
        json={
            "task_id": task_id,
            "selected_tags": {"climate_consumption": {"climate_zone": ["湿热南方"]}},
            "plan_count": 2
        }
    )
    assert gen_resp.status_code == 200
    assert len(gen_resp.json()["data"]["recommendations"]) == 2

@pytest.mark.asyncio
async def test_scenario_4_multi_turn_chat(client, read_sse_stream):
    # Step 1: Create recommendation session based on active tags.
    payload_task = {
        "blogger_url": "https://www.douyin.com/user/MS4wLjABAAA_multiturn",
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

    # Step 2: Turn 1: Add Grapefruit to top notes of plan 1
    chat_resp_1 = await client.post(
        f"/api/v1/fragrance/{session_id}/chat",
        json={"message": "I want to change the top notes of plan 1 to include Grapefruit."}
    )
    assert chat_resp_1.status_code == 200
    assert chat_resp_1.json()["data"]["updated_plans"] is not None
    top_notes = chat_resp_1.json()["data"]["updated_plans"][0]["top_notes"]
    assert any("Grapefruit" in n["name"] for n in top_notes)

    # Step 3: Turn 2: Ask explanation, updated_plans should be null
    chat_resp_2 = await client.post(
        f"/api/v1/fragrance/{session_id}/chat",
        json={"message": "Explain the emotional benefits of grapefruit."}
    )
    assert chat_resp_2.status_code == 200
    assert chat_resp_2.json()["data"]["updated_plans"] is None
    assert "多巴胺" in chat_resp_2.json()["data"]["reply"] or "dopamine" in chat_resp_2.json()["data"]["reply"].lower() or "limonene" in chat_resp_2.json()["data"]["reply"].lower() or "柠檬" in chat_resp_2.json()["data"]["reply"]

    # Step 4: Turn 3: Add Cedarwood to base notes of plan 1
    chat_resp_3 = await client.post(
        f"/api/v1/fragrance/{session_id}/chat",
        json={"message": "Add Cedarwood to base notes of plan 1."}
    )
    assert chat_resp_3.status_code == 200
    assert chat_resp_3.json()["data"]["updated_plans"] is not None
    base_notes = chat_resp_3.json()["data"]["updated_plans"][0]["base_notes"]
    assert any("Cedarwood" in n["name"] for n in base_notes)

    # Step 5: Fetch complete history and verify all message sequence.
    hist_resp = await client.get(f"/api/v1/fragrance/{session_id}/history")
    messages = hist_resp.json()["data"]["messages"]
    # 1 initial + 3 turns * 2 (user + assistant) = 7 messages
    assert len(messages) == 7
    assert messages[0]["role"] == "assistant"
    assert messages[1]["role"] == "user"
    assert messages[2]["role"] == "assistant"
    assert messages[3]["role"] == "user"
    assert messages[4]["role"] == "assistant"
    assert messages[5]["role"] == "user"
    assert messages[6]["role"] == "assistant"

@pytest.mark.asyncio
async def test_scenario_5_admin_model_swapping(client, read_sse_stream):
    # Step 1: Query current active configurations for AI providers.
    response = await client.get("/api/v1/config/ai-providers")
    assert response.status_code == 200

    # Step 2: Change active provider for analysis_task to deepseek and fragrance_reasoning to openai.
    route_resp_1 = await client.put(
        "/api/v1/config/ai-providers/deepseek",
        json={"slot": "analysis_task"},
        headers={"Authorization": "Bearer admin_token"}
    )
    assert route_resp_1.status_code == 200
    
    route_resp_2 = await client.put(
        "/api/v1/config/ai-providers/openai",
        json={"slot": "fragrance_reasoning"},
        headers={"Authorization": "Bearer admin_token"}
    )
    assert route_resp_2.status_code == 200

    # Step 3: Create an analysis task. Verify that the task runner uses DeepSeek.
    payload_task = {
        "blogger_url": "https://www.douyin.com/user/MS4wLjABAAA_t5_swapping",
        "platform": "douyin",
        "analysis_level": "standard"
    }
    create_resp = await client.post("/api/v1/analysis/create", json=payload_task)
    task_id = create_resp.json()["data"]["task_id"]
    await read_sse_stream(client, f"/api/v1/analysis/{task_id}/progress")
    
    from backend.tests.e2e.conftest import ai_routing
    assert ai_routing["analysis_task"]["provider"] == "deepseek"

    # Step 4: Generate recommendations. Verify OpenAI is used.
    payload_gen = {
        "task_id": task_id,
        "selected_tags": {"climate_consumption": {"climate_zone": ["湿热南方"]}},
        "plan_count": 3
    }
    gen_resp = await client.post("/api/v1/fragrance/generate", json=payload_gen)
    assert gen_resp.status_code == 200
    assert ai_routing["fragrance_reasoning"]["provider"] == "openai"

    # Step 5: Change the provider configuration back to defaults (e.g. glm).
    route_resp_3 = await client.put(
        "/api/v1/config/ai-providers/glm",
        json={"slot": "analysis_task"},
        headers={"Authorization": "Bearer admin_token"}
    )
    assert route_resp_3.status_code == 200
    
    route_resp_4 = await client.put(
        "/api/v1/config/ai-providers/glm",
        json={"slot": "fragrance_reasoning"},
        headers={"Authorization": "Bearer admin_token"}
    )
    assert route_resp_4.status_code == 200

    # Step 6: Run a final verification task to ensure routing has successfully reverted.
    assert ai_routing["analysis_task"]["provider"] == "glm"
    assert ai_routing["fragrance_reasoning"]["provider"] == "glm"
