import pytest
import uuid

from app.services.fragrance_service import FragranceEngineError
from tests.e2e.conftest import _seed_completed_task_with_report


async def create_completed_session(client, db, mock_engine, suffix=""):
    """seed completed task + report，然后 generate 创建 session。

    相比旧的 create+read_sse_stream 方式，seed 更稳定（report 字段结构可控、
    不依赖 pipeline 时序）。mock_engine 由 conftest autouse 注入。
    """
    task, _ = _seed_completed_task_with_report(db, suffix)
    payload_gen = {
        "task_id": task.id,
        "selected_tags": {
            "climate_consumption": {"climate_zone": ["湿热南方"]}
        },
        "plan_count": 3
    }
    gen_resp = await client.post("/api/v1/fragrance/generate", json=payload_gen)
    assert gen_resp.status_code == 200, f"generate failed: {gen_resp.text}"
    return gen_resp.json()["data"]["session_id"]


@pytest.mark.asyncio
async def test_f6_post_chat_message(client, db, mock_engine):
    session_id = await create_completed_session(client, db, mock_engine, "1")

    # 配置 mock_engine.chat 返回带 changed base_notes 的 updated_plans
    # （真实 chat 行为由 AI 决定，e2e 用 mock 控制以验证契约字段）
    mock_engine.chat_returns = [(
        "好的，我理解你希望增加方案一的深度和层次感。已将后调调整为木质调。",
        [{
            "plan_id": "plan_1",
            "name": "方案 1",
            "category": "花香木质调",
            "top_notes": [{"name": "佛手柑", "description": "清新", "reason": "活力"}],
            "middle_notes": [{"name": "玫瑰", "description": "浪漫", "reason": "优雅"}],
            "base_notes": [
                {"name": "沉香", "description": "深沉的东方木质", "reason": "增加神秘感", "changed": True},
                {"name": "乌木", "description": "烟熏的暗色木质", "reason": "反差张力", "changed": True},
            ],
            "recommendation_reason": "调整后的方案",
            "fragrance_story": "调整后的故事",
        }]
    )]

    payload = {"message": "Make the base notes for plan 1 more woody."}
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
async def test_f6_retrieve_chat_history(client, db, mock_engine):
    session_id = await create_completed_session(client, db, mock_engine, "2")

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
async def test_f6_get_session_details(client, db, mock_engine):
    session_id = await create_completed_session(client, db, mock_engine, "3")
    response = await client.get(f"/api/v1/fragrance/{session_id}")
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["code"] == 0
    assert res_data["data"]["session_id"] == session_id
    assert "recommendations" in res_data["data"]


# 注：test_f6_chat_streaming_response 已在 M6 改造中删除。
# 原因：真实 /fragrance/{session_id}/chat 端点无 SSE 流式分支（不检查 Accept header），
# 恒返回同步 JSON。stub 的 Accept-based 流式切换是 stub 独有能力，真实 app 未实现。
# 若产品需要流式 chat，需先在 fragrance.py 加 SSE 分支（产品功能新增，超出测试范畴）。


@pytest.mark.asyncio
async def test_f6_regenerate_session(client, db, mock_engine):
    session_id = await create_completed_session(client, db, mock_engine, "5")

    payload = {
        "selected_tags": {
            "climate_consumption": {"climate_zone": ["湿热南方"]}
        },
        "plan_count": 2
    }
    response = await client.post(f"/api/v1/fragrance/{session_id}/regenerate", json=payload)
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["code"] == 0

    # Retrieve history to ensure it was cleared and reset to initial message.
    # 真实 INITIAL_ASSISTANT_MESSAGE 文案为"根据您选择的标签，我为您生成了 X 套..."
    # （generate 与 regenerate 共用同一文案，不含"重新选择"）。断言对齐真实实现。
    history_resp = await client.get(f"/api/v1/fragrance/{session_id}/history")
    messages = history_resp.json()["data"]["messages"]
    assert len(messages) == 1
    assert "生成" in messages[0]["content"]


@pytest.mark.asyncio
async def test_f6_chat_nonexistent_session(client):
    rand_uuid = str(uuid.uuid4())
    payload = {"message": "hello"}
    response = await client.post(f"/api/v1/fragrance/{rand_uuid}/chat", json=payload)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_f6_chat_empty_message(client, db, mock_engine):
    session_id = await create_completed_session(client, db, mock_engine, "6")
    # 真实 ChatRequest.message 有 min_length=1 校验（Pydantic 层）。
    # 传空串触发 422；纯空格 "   " 长度为 3 会通过 schema 校验进入 service（与 stub 的
    # .strip() 判空行为不同）。用例对齐真实：传 "" 期望 422。
    payload = {"message": ""}
    response = await client.post(f"/api/v1/fragrance/{session_id}/chat", json=payload)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_f6_chat_malformed_json_reply(client, db, mock_engine):
    # 真实 app 无"message 含 malformed_json 触发 502"的魔法开关。
    # 通过配置 mock_engine.chat_raise 抛 FragranceEngineError 触发 502（对齐契约）。
    session_id = await create_completed_session(client, db, mock_engine, "7")
    mock_engine.chat_raise = FragranceEngineError("模拟的 AI 引擎 JSON 解析失败")

    payload = {"message": "anything"}
    response = await client.post(f"/api/v1/fragrance/{session_id}/chat", json=payload)
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
