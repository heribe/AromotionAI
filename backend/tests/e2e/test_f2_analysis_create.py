import pytest

@pytest.mark.asyncio
async def test_f2_create_task_standard(client):
    payload = {
        "blogger_url": "https://www.douyin.com/user/MS4wLjABAAA_blogger1",
        "platform": "douyin",
        "analysis_level": "standard"
    }
    response = await client.post("/api/v1/analysis/create", json=payload)
    assert response.status_code in [200, 201]
    res_data = response.json()
    assert res_data["code"] == 0
    assert "task_id" in res_data["data"]
    assert res_data["data"]["status"] == "pending"

@pytest.mark.asyncio
async def test_f2_create_task_custom(client):
    payload = {
        "blogger_url": "https://www.douyin.com/user/MS4wLjABAAA_blogger2",
        "platform": "douyin",
        "analysis_level": "custom",
        "custom_config": {
            "post_selection": {
                "top_count": 4,
                "recent_count": 4,
                "sort_by": "likes"
            },
            "comment": {
                "per_post_count": 30,
                "sort_by": "hot"
            },
            "commenter_analysis": {
                "enabled": True,
                "max_count": 50,
                "analyze_posts": True,
                "posts_per_commenter": 3,
                "analyze_post_content": True,
                "analyze_video": False
            },
            "sub_comment": {
                "enabled": True,
                "count": 5
            },
            "visual_analysis": {
                "cover_analysis": True,
                "video_frame_analysis": True,
                "frames_per_video": 5,
                "analyze_frames_count": 3,
                "fan_cover_mode": "grid",
                "grid_size": 10
            }
        }
    }
    response = await client.post("/api/v1/analysis/create", json=payload)
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["code"] == 0
    assert "task_id" in res_data["data"]

@pytest.mark.asyncio
async def test_f2_create_task_deep_preset(client):
    payload = {
        "blogger_url": "https://www.douyin.com/user/MS4wLjABAAA_blogger3",
        "platform": "douyin",
        "analysis_level": "deep"
    }
    response = await client.post("/api/v1/analysis/create", json=payload)
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["code"] == 0
    assert "task_id" in res_data["data"]

@pytest.mark.asyncio
async def test_f2_parse_url_formats(client):
    urls = [
        "https://www.douyin.com/user/MS4wLjABAAAA_xyz",
        "https://v.douyin.com/abcde/",
        "https://iesdouyin.com/share/user/12345"
    ]
    for url in urls:
        payload = {
            "blogger_url": url,
            "platform": "douyin",
            "analysis_level": "standard"
        }
        response = await client.post("/api/v1/analysis/create", json=payload)
        assert response.status_code == 200
        assert response.json()["code"] == 0

@pytest.mark.asyncio
async def test_f2_platform_auto_detection(client):
    # Omit platform or set to auto
    payload = {
        "blogger_url": "https://www.douyin.com/user/MS4wLjABAAA_auto",
        "platform": "auto",
        "analysis_level": "standard"
    }
    response = await client.post("/api/v1/analysis/create", json=payload)
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["code"] == 0
    
    # Retrieve the task and verify the platform was auto detected as douyin
    task_id = res_data["data"]["task_id"]
    task_resp = await client.get(f"/api/v1/analysis/{task_id}")
    assert task_resp.json()["data"]["platform"] == "douyin"

@pytest.mark.asyncio
async def test_f2_create_task_invalid_blogger_url(client):
    payload = {
        "blogger_url": "not-a-valid-url",
        "platform": "douyin",
        "analysis_level": "standard"
    }
    response = await client.post("/api/v1/analysis/create", json=payload)
    assert response.status_code in [400, 422]

@pytest.mark.asyncio
async def test_f2_create_task_unsupported_platform(client):
    payload = {
        "blogger_url": "https://instagram.com/p/somepost",
        "platform": "instagram",
        "analysis_level": "standard"
    }
    response = await client.post("/api/v1/analysis/create", json=payload)
    assert response.status_code in [400, 422]

@pytest.mark.asyncio
async def test_f2_create_task_missing_cookie(client):
    # Delete the cookie first
    await client.delete("/api/v1/cookies/douyin")
    
    payload = {
        "blogger_url": "https://www.douyin.com/user/MS4wLjABAAA_blogger4",
        "platform": "douyin",
        "analysis_level": "standard"
    }
    response = await client.post("/api/v1/analysis/create", json=payload)
    assert response.status_code == 400
    assert "cookie" in response.json()["detail"].lower()

@pytest.mark.asyncio
async def test_f2_create_task_custom_missing_config(client):
    payload = {
        "blogger_url": "https://www.douyin.com/user/MS4wLjABAAA_blogger5",
        "platform": "douyin",
        "analysis_level": "custom",
        "custom_config": None
    }
    response = await client.post("/api/v1/analysis/create", json=payload)
    assert response.status_code in [400, 422]

@pytest.mark.asyncio
async def test_f2_create_task_out_of_bounds_parameters(client):
    payload = {
        "blogger_url": "https://www.douyin.com/user/MS4wLjABAAA_blogger6",
        "platform": "douyin",
        "analysis_level": "custom",
        "custom_config": {
            "post_selection": {
                "top_count": 500,  # Out of bounds > 100
                "recent_count": -5,  # Out of bounds < 0
                "sort_by": "likes"
            }
        }
    }
    response = await client.post("/api/v1/analysis/create", json=payload)
    assert response.status_code in [400, 422]
