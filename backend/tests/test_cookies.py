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


def test_get_cookie_status(client):
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
    assert len(cookies) == 1
    assert cookies[0]["platform"] == "douyin"
    assert cookies[0]["is_valid"] is True


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
    
    # Query status again, should be empty list
    status_response = client.get("/api/v1/cookies/status")
    assert len(status_response.json()["data"]["cookies"]) == 0
