"""
Tier3 组合场景 e2e 测试（M6 改造后）。

M6 改造中删除的用例（语义与真实架构冲突 / 依赖缺失端点）：
- test_t3_cookie_deletion_mid_task：真实 AnalysisService.run_analysis 不在 step 之间
  检查 cookie 有效性（仅在 create 时校验一次），删除 cookie 后 pipeline 仍会跑完。
  该用例假设的"运行中删 cookie 触发失败"在真实架构下不成立。
- test_t3_task_deletion_impact_on_sse：真实 delete_task 对 collecting/analyzing 态
  抛 TaskStateError→400（task_service.py:374），根本删不掉运行中任务。该用例假设
  的"运行中删 task 使 SSE 流终止"与真实设计冲突。
- test_t3_ai_config_updates_modifying_model_targets：依赖真实 app 不存在的
  /api/v1/config/* 端点族（F7 已从 M6 范围剥离），且原用例读 stub 内存状态。
"""

import pytest
import asyncio

from tests.e2e.conftest import _seed_completed_task_with_report


@pytest.mark.asyncio
async def test_t3_tag_selection_to_recommendation_flow(client, db):
    # 1. seed completed task + report（绕过 pipeline，report 字段结构可控）
    task, _ = _seed_completed_task_with_report(db, "t3_tags")

    # 2. Retrieve tags
    tags_resp = await client.get(f"/api/v1/analysis/{task.id}/tags")
    assert tags_resp.status_code == 200
    dimensions = tags_resp.json()["data"]["dimensions"]

    # Extract subset of tags（取 climate_consumption.climate_zone 的首个标签）
    selected_tags = {
        "climate_consumption": {
            "climate_zone": [dimensions[0]["sub_dimensions"][0]["tags"][0]["name"]]
        }
    }

    # 3. Generate fragrance
    payload_gen = {
        "task_id": task.id,
        "selected_tags": selected_tags,
        "plan_count": 3
    }
    gen_resp = await client.post("/api/v1/fragrance/generate", json=payload_gen)
    assert gen_resp.status_code == 200
    session_id = gen_resp.json()["data"]["session_id"]

    # Verify session is associated with task_id
    sess_detail = await client.get(f"/api/v1/fragrance/{session_id}")
    assert sess_detail.json()["data"]["task_id"] == task.id


@pytest.mark.asyncio
async def test_t3_chat_history_updates_on_recalculations(client, db, mock_engine):
    # seed completed task + report，然后 generate 创建 session
    task, _ = _seed_completed_task_with_report(db, "t3_recalc")

    payload_gen = {
        "task_id": task.id,
        "selected_tags": {"climate_consumption": {"climate_zone": ["湿热南方"]}},
        "plan_count": 3
    }
    gen_resp = await client.post("/api/v1/fragrance/generate", json=payload_gen)
    assert gen_resp.status_code == 200
    session_id = gen_resp.json()["data"]["session_id"]

    # Send feedback chat
    await client.post(
        f"/api/v1/fragrance/{session_id}/chat",
        json={"message": "Make it woody."}
    )

    # Trigger regeneration
    payload_regen = {
        "selected_tags": {"climate_consumption": {"climate_zone": ["湿热南方"]}},
        "plan_count": 2
    }
    regen_resp = await client.post(f"/api/v1/fragrance/{session_id}/regenerate", json=payload_regen)
    assert regen_resp.status_code == 200

    # Get history and verify：regenerate 清空 chat 并重置为初始消息。
    # 真实 INITIAL_ASSISTANT_MESSAGE 文案为"根据您选择的标签，我为您生成了 X 套..."
    # （generate/regenerate 共用同一文案，不含"重新选择"）。断言对齐真实实现。
    hist_resp = await client.get(f"/api/v1/fragrance/{session_id}/history")
    messages = hist_resp.json()["data"]["messages"]
    assert len(messages) == 1
    assert "生成" in messages[0]["content"]


@pytest.mark.asyncio
async def test_t3_task_cascade_deletion(client, db, mock_engine):
    # 1. seed completed task + report
    task, _ = _seed_completed_task_with_report(db, "t3_cascade")

    # 2. Generate recommendation
    payload_gen = {
        "task_id": task.id,
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

    # 4. Delete the task（真实靠 DB 外键 ondelete=CASCADE 级联清理 session/message）
    del_resp = await client.delete(f"/api/v1/analysis/{task.id}")
    assert del_resp.status_code == 200

    # 5. Check cascade deletes: GET task, report, tags, session, history -> 404
    assert (await client.get(f"/api/v1/analysis/{task.id}")).status_code == 404
    assert (await client.get(f"/api/v1/analysis/{task.id}/report")).status_code == 404
    assert (await client.get(f"/api/v1/analysis/{task.id}/tags")).status_code == 404
    assert (await client.get(f"/api/v1/fragrance/{session_id}")).status_code == 404
    assert (await client.get(f"/api/v1/fragrance/{session_id}/history")).status_code == 404


@pytest.mark.asyncio
async def test_t3_multiple_concurrent_tasks_single_cookie(client, upload_douyin_cookie, read_sse_stream):
    # 单 cookie 支撑多个并发任务（真实 TaskManager 支持并发 submit）。
    # mock 模式下各 pipeline 独立跑完，互不干扰。

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
