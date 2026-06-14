"""
Unit tests for FragranceService (Part2 §2.1-2.5 业务层)。

测试策略：
- 使用 conftest.py 的 db fixture（函数级 SQLite）
- 注入 MockFragranceEngine 避免 AI 调用
- 预置 completed AnalysisTask + ProfileReport 作为前置数据

R2 三问自检：
1. 契约闭环：generate/chat/regenerate/get_session/get_history 全覆盖；
   异常路径（task 未完成、标签互斥冲突、引擎失败、session 不存在）逐一验证。
2. 对称性：generate 创建 session+初始消息；regenerate 清空旧 chat；
   chat 中 user 先写、assistant 后写。
3. 外部时序：JSON 解析重试只 1 次；滑窗 20；updated_plans 按 plan_id 合并。
"""

import os
import uuid
import pytest
import datetime
from typing import Optional

os.environ.setdefault("AROMOTION_TEST_MODE", "mock")

from app.services.fragrance_service import (
    FragranceService,
    SessionNotFoundError,
    SessionStateError,
    TaskNotCompletedError,
    TagsValidationError,
    FragranceEngineError,
    SESSION_STATUS_ERROR,
)
from app.engines.base import FragranceEngine
from app.models.analysis import AnalysisTask
from app.models.profile import ProfileReport
from app.models.fragrance import FragranceSession, ChatMessage
from app.schemas.fragrance import GenerateRequest, RegenerateRequest


# ---------- helpers ----------

def _now():
    return datetime.datetime.now(datetime.timezone.utc)


def _seed_completed_task_with_report(db) -> tuple[AnalysisTask, ProfileReport]:
    task = AnalysisTask(
        id=str(uuid.uuid4()),
        platform="douyin",
        blogger_url="https://www.douyin.com/user/MS4w_fragrance_test",
        analysis_level="standard",
        status="completed",
        progress=100,
        current_step="分析完成",
        created_at=_now(),
        updated_at=_now(),
        completed_at=_now(),
    )
    db.add(task)
    db.commit()

    report = ProfileReport(
        id=str(uuid.uuid4()),
        task_id=task.id,
        climate_consumption={
            "climate_zone": {"湿热南方": 60.0, "干燥北方": 40.0},
            "summary": "偏向湿热南方气候带",
        },
        fragrance_consumption={
            "price_tier": {"轻奢入门": 50.0},
            "summary": "轻奢消费偏好",
        },
        fashion_fragrance_map={
            "fashion_style": {"甜美系": 40.0},
            "summary": "甜美系穿搭",
        },
        lifestyle_scenario={
            "core_interest": {"日常自拍": 30.0},
            "summary": "自拍分享生活方式",
        },
        overall_summary="测试整体画像摘要",
        full_report_markdown="## 测试报告",
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return task, report


def _valid_selected_tags() -> dict:
    return {
        "climate_consumption": {
            "climate_zone": ["湿热南方"],
            "city_tier": ["一线/新一线"],
        },
        "fragrance_consumption": {
            "price_tier": ["轻奢入门"],
        },
    }


def _mock_ai_result(plan_count: int = 2) -> dict:
    return {
        "iceberg_analysis": {
            "surface": "显性层分析",
            "middle": "情感层分析",
            "deep": "深层分析",
        },
        "recommendations": [
            {
                "plan_id": f"plan_{i+1}",
                "name": f"方案 {i+1}",
                "category": "花果香调",
                "top_notes": [{"name": "佛手柑", "description": "清新", "reason": "活力"}],
                "middle_notes": [{"name": "玫瑰", "description": "浪漫", "reason": "优雅"}],
                "base_notes": [{"name": "白檀", "description": "温暖", "reason": "收尾"}],
                "recommendation_reason": "推荐理由",
                "fragrance_story": "灵感故事",
            }
            for i in range(plan_count)
        ],
    }


class MockFragranceEngine(FragranceEngine):
    """可配置的 mock 引擎：按队列返回 generate / chat 结果。"""

    def __init__(self):
        self.generate_returns: list[dict] = []
        self.chat_returns: list[tuple[str, Optional[list[dict]]]] = []
        self.generate_call_count = 0
        self.chat_call_count = 0
        self.generate_raise: Optional[Exception] = None

    async def generate(self, fused_profile, selected_tags, plan_count=3):
        self.generate_call_count += 1
        if self.generate_raise:
            raise self.generate_raise
        if self.generate_returns:
            return self.generate_returns.pop(0)
        return _mock_ai_result(plan_count)

    async def chat(self, history, current_plans, user_message, selected_tags):
        self.chat_call_count += 1
        if self.chat_returns:
            return self.chat_returns.pop(0)
        return ("好的，已理解您的需求。", None)


@pytest.fixture
def service_with_mock(db):
    engine = MockFragranceEngine()
    svc = FragranceService(db, engine=engine)
    return svc, engine


# ---------- generate ----------

@pytest.mark.asyncio
async def test_generate_success(db, service_with_mock):
    svc, engine = service_with_mock
    task, _ = _seed_completed_task_with_report(db)
    req = GenerateRequest(task_id=task.id, selected_tags=_valid_selected_tags(), plan_count=2)

    data = await svc.generate(req)

    assert data.status == "completed"
    assert data.session_id
    assert len(data.recommendations) == 2
    assert data.iceberg_analysis.surface == "显性层分析"
    assert data.warnings == []

    # 验证 session 落库 + 初始 assistant 消息
    session = db.query(FragranceSession).filter(FragranceSession.id == data.session_id).first()
    assert session is not None
    assert session.status == "completed"
    msgs = db.query(ChatMessage).filter(ChatMessage.session_id == session.id).all()
    assert len(msgs) == 1
    assert msgs[0].role == "assistant"
    assert "2 套香调方案" in msgs[0].content


@pytest.mark.asyncio
async def test_generate_task_not_completed(db, service_with_mock):
    svc, _ = service_with_mock
    task = AnalysisTask(
        id=str(uuid.uuid4()),
        platform="douyin",
        blogger_url="https://www.douyin.com/user/x",
        analysis_level="standard",
        status="pending",
        progress=0,
        current_step="准备",
        created_at=_now(),
        updated_at=_now(),
    )
    db.add(task)
    db.commit()

    req = GenerateRequest(task_id=task.id, selected_tags=_valid_selected_tags())
    with pytest.raises(TaskNotCompletedError):
        await svc.generate(req)


@pytest.mark.asyncio
async def test_generate_task_not_found(db, service_with_mock):
    svc, _ = service_with_mock
    req = GenerateRequest(task_id=str(uuid.uuid4()), selected_tags=_valid_selected_tags())
    with pytest.raises(Exception):  # TaskNotFoundError 是 KeyError 子类
        await svc.generate(req)


@pytest.mark.asyncio
async def test_generate_invalid_tags_mutex(db, service_with_mock):
    svc, _ = service_with_mock
    task, _ = _seed_completed_task_with_report(db)
    # climate_zone 互斥组选 2 个
    bad_tags = {
        "climate_consumption": {
            "climate_zone": ["湿热南方", "干燥北方"],
        }
    }
    req = GenerateRequest(task_id=task.id, selected_tags=bad_tags)
    with pytest.raises(TagsValidationError):
        await svc.generate(req)


@pytest.mark.asyncio
async def test_generate_weight_normalization(db, service_with_mock):
    svc, _ = service_with_mock
    task, _ = _seed_completed_task_with_report(db)
    req = GenerateRequest(
        task_id=task.id,
        selected_tags=_valid_selected_tags(),
        blogger_weight=0.3,
        audience_weight=0.4,  # 总和 0.7 != 1.0
    )
    data = await svc.generate(req)
    assert len(data.warnings) == 1
    assert "auto-normalized" in data.warnings[0]


@pytest.mark.asyncio
async def test_generate_json_parse_retry_success(db, service_with_mock):
    svc, engine = service_with_mock
    task, _ = _seed_completed_task_with_report(db)
    # 第一次返回空 recommendations（模拟解析失败），第二次正常
    engine.generate_returns = [
        {"iceberg_analysis": {"surface": "", "middle": "", "deep": ""}, "recommendations": []},
        _mock_ai_result(2),
    ]
    req = GenerateRequest(task_id=task.id, selected_tags=_valid_selected_tags(), plan_count=2)
    data = await svc.generate(req)
    assert len(data.recommendations) == 2
    assert engine.generate_call_count == 2


@pytest.mark.asyncio
async def test_generate_retry_still_fails(db, service_with_mock):
    svc, engine = service_with_mock
    task, _ = _seed_completed_task_with_report(db)
    engine.generate_returns = [
        {"iceberg_analysis": {}, "recommendations": []},
        {"iceberg_analysis": {}, "recommendations": []},
    ]
    req = GenerateRequest(task_id=task.id, selected_tags=_valid_selected_tags())
    with pytest.raises(FragranceEngineError):
        await svc.generate(req)

    # session 标 error 但保留
    session = db.query(FragranceSession).first()
    assert session is not None
    assert session.status == SESSION_STATUS_ERROR


@pytest.mark.asyncio
async def test_generate_ai_exception(db, service_with_mock):
    svc, engine = service_with_mock
    task, _ = _seed_completed_task_with_report(db)
    engine.generate_raise = RuntimeError("AI network timeout")
    req = GenerateRequest(task_id=task.id, selected_tags=_valid_selected_tags())
    with pytest.raises(FragranceEngineError):
        await svc.generate(req)
    session = db.query(FragranceSession).first()
    assert session.status == SESSION_STATUS_ERROR


# ---------- chat ----------

@pytest.mark.asyncio
async def test_chat_success_no_plan_update(db, service_with_mock):
    svc, _ = service_with_mock
    task, _ = _seed_completed_task_with_report(db)
    req = GenerateRequest(task_id=task.id, selected_tags=_valid_selected_tags(), plan_count=1)
    gen_data = await svc.generate(req)

    chat_data = await svc.chat(gen_data.session_id, "这个方案适合夏天吗？")
    assert chat_data.reply
    assert chat_data.updated_plans is None
    assert chat_data.message_id

    # 验证消息序列：初始 assistant + user + assistant
    msgs = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == gen_data.session_id)
        .order_by(ChatMessage.created_at.asc())
        .all()
    )
    assert len(msgs) == 3
    assert [m.role for m in msgs] == ["assistant", "user", "assistant"]


@pytest.mark.asyncio
async def test_chat_success_with_updated_plans(db, service_with_mock):
    svc, engine = service_with_mock
    task, _ = _seed_completed_task_with_report(db)
    req = GenerateRequest(task_id=task.id, selected_tags=_valid_selected_tags(), plan_count=1)
    gen_data = await svc.generate(req)

    # 模拟 chat 返回修改后的 plan_1
    engine.chat_returns = [
        ("已将后调改为沉香。", [
            {
                "plan_id": "plan_1",
                "name": "更新后的方案",
                "category": "东方木质调",
                "top_notes": [],
                "middle_notes": [],
                "base_notes": [{"name": "沉香", "description": "深沉", "reason": "深度", "changed": True}],
                "recommendation_reason": "修改理由",
                "fragrance_story": "新故事",
            }
        ]),
    ]
    chat_data = await svc.chat(gen_data.session_id, "后调换成沉香")
    assert chat_data.updated_plans is not None
    assert len(chat_data.updated_plans) == 1
    assert chat_data.updated_plans[0].plan_id == "plan_1"

    # 验证 session.recommendations 已合并
    session = db.query(FragranceSession).filter(FragranceSession.id == gen_data.session_id).first()
    plans = session.recommendations["recommendations"]
    assert len(plans) == 1
    assert plans[0]["name"] == "更新后的方案"
    assert plans[0]["base_notes"][0]["name"] == "沉香"


@pytest.mark.asyncio
async def test_chat_session_not_found(db, service_with_mock):
    svc, _ = service_with_mock
    with pytest.raises(SessionNotFoundError):
        await svc.chat(str(uuid.uuid4()), "hello")


@pytest.mark.asyncio
async def test_chat_session_in_error_state(db, service_with_mock):
    svc, _ = service_with_mock
    task, _ = _seed_completed_task_with_report(db)
    req = GenerateRequest(task_id=task.id, selected_tags=_valid_selected_tags())
    gen_data = await svc.generate(req)

    # 手动把 session 标 error
    session = db.query(FragranceSession).filter(FragranceSession.id == gen_data.session_id).first()
    session.status = SESSION_STATUS_ERROR
    db.commit()

    with pytest.raises(SessionStateError):
        await svc.chat(gen_data.session_id, "hello")


@pytest.mark.asyncio
async def test_chat_user_message_persisted_on_engine_failure(db, service_with_mock):
    svc, engine = service_with_mock
    task, _ = _seed_completed_task_with_report(db)
    req = GenerateRequest(task_id=task.id, selected_tags=_valid_selected_tags())
    gen_data = await svc.generate(req)

    # 模拟 chat 引擎抛异常
    async def fail_chat(*args, **kwargs):
        raise RuntimeError("chat AI down")
    engine.chat = fail_chat

    with pytest.raises(FragranceEngineError):
        await svc.chat(gen_data.session_id, "我的消息")

    # user 消息应该已落库（即使 AI 失败）
    msgs = db.query(ChatMessage).filter(ChatMessage.session_id == gen_data.session_id).all()
    user_msgs = [m for m in msgs if m.role == "user"]
    assert len(user_msgs) == 1
    assert user_msgs[0].content == "我的消息"


# ---------- regenerate ----------

@pytest.mark.asyncio
async def test_regenerate_clears_old_chat(db, service_with_mock):
    svc, _ = service_with_mock
    task, _ = _seed_completed_task_with_report(db)
    req = GenerateRequest(task_id=task.id, selected_tags=_valid_selected_tags(), plan_count=1)
    gen_data = await svc.generate(req)

    # 先 chat 一轮
    await svc.chat(gen_data.session_id, "咨询")

    # 验证有消息
    msgs_before = db.query(ChatMessage).filter(ChatMessage.session_id == gen_data.session_id).count()
    assert msgs_before == 3  # 初始 assistant + user + assistant

    # regenerate
    reg_req = RegenerateRequest(plan_count=2)
    reg_data = await svc.regenerate(gen_data.session_id, reg_req)

    assert len(reg_data.recommendations) == 2
    # 旧 chat 清空，只剩新的初始 assistant 消息
    msgs_after = db.query(ChatMessage).filter(ChatMessage.session_id == gen_data.session_id).count()
    assert msgs_after == 1
    last_msg = db.query(ChatMessage).filter(ChatMessage.session_id == gen_data.session_id).first()
    assert last_msg.role == "assistant"


@pytest.mark.asyncio
async def test_regenerate_with_new_tags(db, service_with_mock):
    svc, _ = service_with_mock
    task, _ = _seed_completed_task_with_report(db)
    req = GenerateRequest(task_id=task.id, selected_tags=_valid_selected_tags(), plan_count=1)
    gen_data = await svc.generate(req)

    new_tags = {
        "climate_consumption": {"climate_zone": ["干燥北方"]},
    }
    reg_req = RegenerateRequest(selected_tags=new_tags, plan_count=1)
    await svc.regenerate(gen_data.session_id, reg_req)

    session = db.query(FragranceSession).filter(FragranceSession.id == gen_data.session_id).first()
    assert session.selected_tags == new_tags


# ---------- get_session / get_history ----------

@pytest.mark.asyncio
async def test_get_session_detail(db, service_with_mock):
    svc, _ = service_with_mock
    task, _ = _seed_completed_task_with_report(db)
    req = GenerateRequest(task_id=task.id, selected_tags=_valid_selected_tags(), plan_count=2)
    gen_data = await svc.generate(req)

    detail = svc.get_session_detail(gen_data.session_id)
    assert detail.task_id == task.id
    assert len(detail.recommendations) == 2
    assert detail.iceberg_analysis.surface == "显性层分析"
    assert detail.status == "completed"


def test_get_session_detail_not_found(db, service_with_mock):
    svc, _ = service_with_mock
    with pytest.raises(SessionNotFoundError):
        svc.get_session_detail(str(uuid.uuid4()))


@pytest.mark.asyncio
async def test_get_history(db, service_with_mock):
    svc, _ = service_with_mock
    task, _ = _seed_completed_task_with_report(db)
    req = GenerateRequest(task_id=task.id, selected_tags=_valid_selected_tags())
    gen_data = await svc.generate(req)
    await svc.chat(gen_data.session_id, "咨询问题")

    history = svc.get_history(gen_data.session_id)
    assert len(history.messages) == 3
    assert history.messages[0].role == "assistant"
    assert history.messages[1].role == "user"
    assert history.messages[2].role == "assistant"


# ---------- 滑窗测试 ----------

@pytest.mark.asyncio
async def test_chat_history_sliding_window(db, service_with_mock):
    """验证滑窗：预置 > MAX_HISTORY 条消息后调 chat，engine 收到的 history 截断到 20。"""
    from app.engines.prompt_engine import MAX_HISTORY_MESSAGES

    svc, engine = service_with_mock
    task, _ = _seed_completed_task_with_report(db)
    req = GenerateRequest(task_id=task.id, selected_tags=_valid_selected_tags())
    gen_data = await svc.generate(req)

    # 手动插入 25 条历史消息
    base_time = _now()
    for i in range(25):
        role = "user" if i % 2 == 0 else "assistant"
        db.add(ChatMessage(
            id=str(uuid.uuid4()),
            session_id=gen_data.session_id,
            role=role,
            content=f"历史消息 {i}",
            updated_plans=None,
            created_at=base_time + datetime.timedelta(seconds=i),
        ))
    db.commit()

    captured_history = []
    original_chat = engine.chat

    async def capture_chat(history, current_plans, user_message, selected_tags):
        captured_history.extend(history)
        return await original_chat(history, current_plans, user_message, selected_tags)
    engine.chat = capture_chat

    await svc.chat(gen_data.session_id, "新问题")

    # 滑窗：engine 收到的 history 应为最近 20 条（不含刚 append 的 user message，
    # 因为 user message 在 engine 调用前已写入 DB，但 history 在写之前截取）
    # 实际：history 在写 user_msg 之前查询，所以是 25 条取最后 20 条
    assert len(captured_history) == MAX_HISTORY_MESSAGES


# ---------- 权重边界 ----------

@pytest.mark.asyncio
async def test_generate_zero_weights_fallback(db, service_with_mock):
    svc, _ = service_with_mock
    task, _ = _seed_completed_task_with_report(db)
    req = GenerateRequest(
        task_id=task.id,
        selected_tags=_valid_selected_tags(),
        blogger_weight=0.0,
        audience_weight=0.0,
    )
    data = await svc.generate(req)
    assert any("fell back" in w for w in data.warnings)
