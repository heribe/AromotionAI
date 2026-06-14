import pytest
import asyncio

# M6 改造决策：F7 config 端点族整体 skip。
# 真实 app 未实现 /api/v1/config/* 路由模块（presets/ai-providers/routing/status），
# 且部分用例原依赖 stub conftest 的内部状态变量（ai_routing）。
# 待实现 config 模块后解除 skip。详见 PROGRESS.md "M6 e2e 改造决策记录"。
pytestmark = pytest.mark.skip(
    reason="F7 config 端点族待实现：真实 app 无 /api/v1/config/* 路由模块"
)


@pytest.mark.asyncio
async def test_f7_get_presets(client):
    response = await client.get("/api/v1/config/analysis-levels")
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["code"] == 0
    presets = res_data["data"]["presets"]
    assert len(presets) > 0
    assert any(p["level"] == "standard" for p in presets)

@pytest.mark.asyncio
async def test_f7_get_ai_providers(client):
    response = await client.get("/api/v1/config/ai-providers")
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["code"] == 0
    providers = res_data["data"]["providers"]
    assert len(providers) > 0
    assert any(p["name"] == "glm" for p in providers)

@pytest.mark.asyncio
async def test_f7_update_ai_routing(client):
    payload = {
        "slot": "fragrance_reasoning",
        "model": "gpt-4o"
    }
    # Update config with authorization header
    response = await client.put(
        "/api/v1/config/ai-providers/openai",
        json=payload,
        headers={"Authorization": "Bearer admin_token"}
    )
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["code"] == 0
    
    # Verify via direct mock state or config check if possible
    # We can check that the slot was updated
    from backend.tests.e2e.conftest import ai_routing
    assert ai_routing["fragrance_reasoning"]["provider"] == "openai"
    assert ai_routing["fragrance_reasoning"]["model"] == "gpt-4o"

@pytest.mark.asyncio
async def test_f7_get_sys_health(client):
    response = await client.get("/api/v1/config/status")
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["code"] == 0
    assert res_data["data"]["database"] == "connected"

@pytest.mark.asyncio
async def test_f7_modify_api_keys(client):
    payload = {
        "api_key": "sk-newkey123...",
        "endpoint": "https://api.deepseek.com/v1"
    }
    response = await client.put(
        "/api/v1/config/ai-providers/deepseek",
        json=payload,
        headers={"Authorization": "Bearer admin_token"}
    )
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["code"] == 0
    
    # Verify keys
    from backend.tests.e2e.conftest import ai_routing
    # DeepSeek provider endpoint should be updated
    for config in ai_routing.values():
        if config["provider"] == "deepseek":
            assert config["api_key"] == "sk-newkey123..."
            assert config["endpoint"] == "https://api.deepseek.com/v1"

@pytest.mark.asyncio
async def test_f7_update_nonexistent_provider(client):
    payload = {
        "slot": "fragrance_reasoning",
        "model": "unknown"
    }
    response = await client.put(
        "/api/v1/config/ai-providers/unknown_provider",
        json=payload,
        headers={"Authorization": "Bearer admin_token"}
    )
    assert response.status_code == 404

@pytest.mark.asyncio
async def test_f7_update_config_invalid_fields(client):
    # Send non-string slot/model
    payload = {
        "slot": 12345,  # Should be string
        "model": "gpt-4"
    }
    response = await client.put(
        "/api/v1/config/ai-providers/openai",
        json=payload,
        headers={"Authorization": "Bearer admin_token"}
    )
    assert response.status_code == 422

@pytest.mark.asyncio
async def test_f7_unauthorized_config_access(client):
    payload = {
        "slot": "fragrance_reasoning",
        "model": "gpt-4o"
    }
    # No Authorization header
    response = await client.put(
        "/api/v1/config/ai-providers/openai",
        json=payload
    )
    assert response.status_code in [401, 403]

@pytest.mark.asyncio
async def test_f7_get_presets_unsupported_level(client):
    response = await client.get("/api/v1/config/analysis-levels/unknown_level")
    assert response.status_code == 404

@pytest.mark.asyncio
async def test_f7_concurrent_routing_updates(client):
    payloads = [
        {"slot": "fragrance_reasoning", "model": f"model_{i}"}
        for i in range(10)
    ]
    
    async def make_request(p):
        return await client.put(
            "/api/v1/config/ai-providers/openai",
            json=p,
            headers={"Authorization": "Bearer admin_token"}
        )
        
    tasks = [make_request(p) for p in payloads]
    responses = await asyncio.gather(*tasks)
    
    for resp in responses:
        assert resp.status_code == 200
        assert resp.json()["code"] == 0
