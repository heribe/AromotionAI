"""
Integration tests for the Cookie Management APIs.

R2 Three-Question Self-Check:
1. Contract Closure: Validates error responses (400) and successful payloads (200, code=0) to ensure the REST contracts behave as designed.
2. Symmetry: Validates both state creation (upload) and state destruction (delete), ensuring filesystem backup synchronization.
3. External Timing: Test flows simulate sequential browser-to-backend operations.
"""

import json

def test_upload_cookie_success(client):
    cookie_payload = [{"name": "sessionid", "value": "test-token-12345", "domain": ".douyin.com"}]
    files = {
        "file": ("douyin.json", json.dumps(cookie_payload), "application/json")
    }
    data = {"platform": "douyin"}
    
    response = client.post("/api/v1/cookies/upload", data=data, files=files)
    assert response.status_code == 200
    res_json = response.json()
    assert res_json["code"] == 0
    assert res_json["data"]["platform"] == "douyin"
    assert res_json["data"]["is_valid"] is True


def test_upload_cookie_invalid_platform(client):
    cookie_payload = [{"name": "sessionid", "value": "test-token", "domain": ".invalid.com"}]
    files = {
        "file": ("invalid.json", json.dumps(cookie_payload), "application/json")
    }
    data = {"platform": "unsupported_platform"}
    
    response = client.post("/api/v1/cookies/upload", data=data, files=files)
    assert response.status_code == 400
    assert "不支持的平台" in response.json()["detail"]


def test_upload_cookie_invalid_json(client):
    files = {
        "file": ("douyin.json", "this-is-not-valid-json-format", "application/json")
    }
    data = {"platform": "douyin"}
    
    response = client.post("/api/v1/cookies/upload", data=data, files=files)
    assert response.status_code == 400
    assert "无效的 Cookie 文件格式" in response.json()["detail"]


def test_get_cookie_status_returns_all_supported_platforms(client):
    """status 端点必须返回所有支持平台；未配置的标记 is_valid=False 且时间戳为 None。"""
    cookie_payload = [{"name": "sessionid", "value": "test-token", "domain": ".douyin.com"}]
    files = {
        "file": ("douyin.json", json.dumps(cookie_payload), "application/json")
    }
    # Upload one first
    client.post("/api/v1/cookies/upload", data={"platform": "douyin"}, files=files)

    response = client.get("/api/v1/cookies/status")
    assert response.status_code == 200
    res_json = response.json()
    assert res_json["code"] == 0
    cookies = res_json["data"]["cookies"]
    # 所有支持平台都列出（douyin / xiaohongshu / taobao）
    assert len(cookies) == 3
    by_platform = {c["platform"]: c for c in cookies}
    # douyin 已配置
    assert by_platform["douyin"]["is_valid"] is True
    assert by_platform["douyin"]["uploaded_at"] is not None
    # 其余两个未配置
    for p in ("xiaohongshu", "taobao"):
        assert by_platform[p]["is_valid"] is False
        assert by_platform[p]["uploaded_at"] is None
        assert by_platform[p]["last_checked_at"] is None


def test_get_cookie_status_empty_returns_all_unconfigured(client):
    """没有任何 cookie 配置时，status 仍应返回 3 个支持平台，全部 is_valid=False。"""
    response = client.get("/api/v1/cookies/status")
    assert response.status_code == 200
    cookies = response.json()["data"]["cookies"]
    assert len(cookies) == 3
    assert all(c["is_valid"] is False for c in cookies)
    assert all(c["uploaded_at"] is None for c in cookies)


def test_delete_cookie(client):
    cookie_payload = [{"name": "sessionid", "value": "test-token", "domain": ".douyin.com"}]
    files = {
        "file": ("douyin.json", json.dumps(cookie_payload), "application/json")
    }
    client.post("/api/v1/cookies/upload", data={"platform": "douyin"}, files=files)

    # Delete the cookie physically
    response = client.delete("/api/v1/cookies/douyin")
    assert response.status_code == 200
    assert response.json()["data"]["deleted"] is True

    # Query status again: douyin 现在应标记为未配置
    status_response = client.get("/api/v1/cookies/status")
    cookies = status_response.json()["data"]["cookies"]
    assert len(cookies) == 3  # 仍是 3 个支持平台
    douyin = [c for c in cookies if c["platform"] == "douyin"][0]
    assert douyin["is_valid"] is False
    assert douyin["uploaded_at"] is None
