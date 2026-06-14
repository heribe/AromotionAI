import pytest
import json

@pytest.mark.asyncio
async def test_f1_upload_valid_cookie(client):
    file_content = b'[{"name": "sessionid", "value": "mycookie123"}]'
    response = await client.post(
        "/api/v1/cookies/upload",
        data={"platform": "douyin"},
        files={"file": ("cookie.json", file_content)}
    )
    assert response.status_code in [200, 201]
    res_data = response.json()
    assert res_data["code"] == 0
    assert res_data["data"]["platform"] == "douyin"
    assert res_data["data"]["is_valid"] is True

@pytest.mark.asyncio
async def test_f1_get_status_empty(client):
    # Ensure there is no cookie first
    await client.delete("/api/v1/cookies/douyin")
    await client.delete("/api/v1/cookies/xiaohongshu")
    await client.delete("/api/v1/cookies/taobao")
    
    response = await client.get("/api/v1/cookies/status")
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["code"] == 0
    cookies_list = res_data["data"]["cookies"]
    # Verify all platforms show is_valid as False or uploaded_at as null
    for cookie in cookies_list:
        assert cookie["is_valid"] is False
        assert cookie["uploaded_at"] is None

@pytest.mark.asyncio
async def test_f1_get_status_after_upload(client):
    # Upload a cookie
    file_content = b'[{"name": "sessionid", "value": "cookie123"}]'
    await client.post(
        "/api/v1/cookies/upload",
        data={"platform": "douyin"},
        files={"file": ("cookie.json", file_content)}
    )
    
    response = await client.get("/api/v1/cookies/status")
    assert response.status_code == 200
    res_data = response.json()
    cookies_list = res_data["data"]["cookies"]
    douyin_cookie = next(c for c in cookies_list if c["platform"] == "douyin")
    assert douyin_cookie["is_valid"] is True
    assert douyin_cookie["uploaded_at"] is not None

@pytest.mark.asyncio
async def test_f1_overwrite_cookie(client):
    # First upload
    await client.post(
        "/api/v1/cookies/upload",
        data={"platform": "douyin"},
        files={"file": ("cookie.json", b'[{"name":"a","value":"1"}]')}
    )
    # Overwrite upload
    response = await client.post(
        "/api/v1/cookies/upload",
        data={"platform": "douyin"},
        files={"file": ("cookie.json", b'[{"name":"a","value":"2"}]')}
    )
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["code"] == 0
    assert res_data["data"]["is_valid"] is True

@pytest.mark.asyncio
async def test_f1_delete_cookie(client):
    # Upload first
    await client.post(
        "/api/v1/cookies/upload",
        data={"platform": "douyin"},
        files={"file": ("cookie.json", b'[]')}
    )
    # Delete
    response = await client.delete("/api/v1/cookies/douyin")
    assert response.status_code in [200, 204]
    
    # Check status
    status_resp = await client.get("/api/v1/cookies/status?platform=douyin")
    res_data = status_resp.json()
    cookies_list = res_data["data"]["cookies"]
    douyin_cookie = next(c for c in cookies_list if c["platform"] == "douyin")
    assert douyin_cookie["is_valid"] is False

@pytest.mark.asyncio
async def test_f1_upload_invalid_file_format(client):
    response = await client.post(
        "/api/v1/cookies/upload",
        data={"platform": "douyin"},
        files={"file": ("cookie.txt", b'not a json content')}
    )
    assert response.status_code in [400, 422]
    res_data = response.json()
    assert "detail" in res_data

@pytest.mark.asyncio
async def test_f1_upload_empty_file(client):
    response = await client.post(
        "/api/v1/cookies/upload",
        data={"platform": "douyin"},
        files={"file": ("cookie.json", b'')}
    )
    assert response.status_code == 400

@pytest.mark.asyncio
async def test_f1_query_nonexistent_platform(client):
    response = await client.get("/api/v1/cookies/status?platform=unknown")
    assert response.status_code in [400, 422]

@pytest.mark.asyncio
async def test_f1_delete_missing_cookie(client):
    # Verify it handles deletion of missing cookie with 404 or gracefully
    # Let's ensure xiaohongshu doesn't exist
    await client.delete("/api/v1/cookies/xiaohongshu")
    
    response = await client.delete("/api/v1/cookies/xiaohongshu")
    # conftest.py raises 404 if not found
    assert response.status_code == 404

@pytest.mark.asyncio
async def test_f1_expired_cookie_detection(client):
    # Upload first
    await client.post(
        "/api/v1/cookies/upload",
        data={"platform": "douyin"},
        files={"file": ("cookie.json", b'[]')}
    )
    # Modify state directly if possible, or trigger validate when we know it is invalid
    # In conftest, we can manually toggle the cookie to invalid to simulate expiration
    from backend.tests.e2e.conftest import cookies as mock_cookies
    mock_cookies["douyin"]["is_valid"] = False
    
    response = await client.post("/api/v1/cookies/validate/douyin")
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["data"]["is_valid"] is False
