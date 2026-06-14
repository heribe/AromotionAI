"""
FragranceService: 香调推荐业务编排层 (Part2 §2.1-2.5)。

封装 FragranceSession / ChatMessage 的生命周期管理，将 HTTP 层与
FragranceEngine 解耦。负责：标签校验、画像融合、JSON 解析重试、
聊天历史滑窗、方案增量合并。

R2 Three-Question Self-Check:
1. Contract Closure: 每个方法对应文档 §2.x 的一个接口契约；异常类型由
   API 层捕获并映射为 HTTP 状态码。generate 失败时 session 标 error 但
   不删除（便于排障），形成完整状态闭环。
2. Symmetry: generate 创建 session + 初始消息；regenerate 覆盖方案并清空
   chat 历史（创建/销毁对称）；chat 中 user 消息先落库、assistant 后落库，
   AI 失败时 user 痕迹保留。
3. External Timing: JSON 解析失败仅重试 1 次（避免 AI 成本失控）；session
   状态机 generating -> completed|error 严格单向；chat 滑窗在调用 engine
   前完成截断，保证 engine 收到的上下文确定。
"""

import uuid
import logging
import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.engines.base import FragranceEngine
from app.engines import get_engine
from app.models.analysis import AnalysisTask
from app.models.profile import ProfileReport
from app.models.blogger import BloggerProfile
from app.models.fragrance import FragranceSession, ChatMessage
from app.services.task_service import (
    TaskNotFoundError,
    MUTUALLY_EXCLUSIVE_GROUPS,
)
from app.schemas.fragrance import (
    GenerateRequest,
    GenerateData,
    ChatData,
    RegenerateRequest,
    SessionDetailData,
    ChatHistoryData,
    ChatMessageItem,
    IcebergAnalysis,
    FragrancePlan,
)

logger = logging.getLogger(__name__)

SESSION_STATUS_GENERATING = "generating"
SESSION_STATUS_COMPLETED = "completed"
SESSION_STATUS_ERROR = "error"

# 初始 assistant 消息的固定文案（§2.1 业务逻辑 + §2.5 history msg_1）
INITIAL_ASSISTANT_MESSAGE = "根据您选择的标签，我为您生成了 {plan_count} 套香调方案，可在下方查看详情并进行对话微调。"


# ---------- 自定义异常 ----------

class SessionNotFoundError(KeyError):
    """Session 不存在 (HTTP 404)。"""


class SessionStateError(ValueError):
    """Session 状态不允许此操作 (HTTP 400)。"""


class TaskNotCompletedError(ValueError):
    """分析任务未完成 (HTTP 400)。"""


class TagsValidationError(ValueError):
    """标签集合违反互斥组或结构约束 (HTTP 422)。"""


class FragranceEngineError(RuntimeError):
    """引擎调用失败（JSON 解析重试耗尽或 AI 异常）(HTTP 500/502)。"""


def _now() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)


class FragranceService:
    def __init__(self, db: Session, engine: Optional[FragranceEngine] = None) -> None:
        self.db = db
        self.engine = engine or get_engine()

    # ---------- 校验 ----------

    @staticmethod
    def _validate_tags(selected_tags: dict) -> None:
        """校验 selected_tags 结构与互斥组约束（§9.2）。

        selected_tags 预期结构: {dimension_id: {sub_id: [tag_name, ...]}}。
        """
        if not isinstance(selected_tags, dict) or not selected_tags:
            raise TagsValidationError("selected_tags must be a non-empty dict")

        for dim_id, mutex_map in MUTUALLY_EXCLUSIVE_GROUPS.items():
            dim_tags = selected_tags.get(dim_id)
            if not isinstance(dim_tags, dict):
                continue
            for sub_id, _group in mutex_map.items():
                tags = dim_tags.get(sub_id)
                if isinstance(tags, list) and len(tags) > 1:
                    raise TagsValidationError(
                        f"Sub-dimension '{dim_id}/{sub_id}' is mutually exclusive: "
                        f"at most 1 tag allowed, got {len(tags)}"
                    )

    @staticmethod
    def _normalize_weights(
        blogger_weight: float, audience_weight: float
    ) -> tuple[float, float, list[str]]:
        """权重归一化。返回 (bw, aw, warnings)。"""
        warnings: list[str] = []
        total = blogger_weight + audience_weight
        if total <= 0:
            # 两者都为 0 时回退到默认均分
            return (0.5, 0.5, ["blogger_weight + audience_weight = 0; fell back to 0.5/0.5"])
        if abs(total - 1.0) > 1e-6:
            bw = blogger_weight / total
            aw = audience_weight / total
            warnings.append(
                f"blogger_weight + audience_weight = {total:.2f} (!= 1.0); "
                f"auto-normalized to {bw:.2f}/{aw:.2f}"
            )
            return (bw, aw, warnings)
        return (blogger_weight, audience_weight, warnings)

    # ---------- 画像融合 ----------

    def _build_fused_profile(
        self,
        task_id: str,
        report: ProfileReport,
        blogger_weight: float,
        audience_weight: float,
    ) -> str:
        """构造融合画像文本（按权重标注）。"""
        blogger = (
            self.db.query(BloggerProfile)
            .filter(BloggerProfile.task_id == task_id)
            .first()
        )

        parts: list[str] = [
            f"【权重】博主画像 {blogger_weight:.0%} / 粉丝画像 {audience_weight:.0%}"
        ]

        # 博主侧（ BloggerProfile 的基本属性 + overall_summary 提供调性）
        if blogger:
            parts.append(
                "【博主侧】"
                f"昵称={blogger.nickname or '未知'}, "
                f"性别={blogger.gender or '未知'}, "
                f"年龄={blogger.age or '未知'}, "
                f"地域={blogger.province or ''}{blogger.city or ''}"
            )
        if report.overall_summary:
            parts.append(f"【整体画像摘要】{report.overall_summary}")

        # 粉丝侧：四个维度的 summary 字段
        fan_summaries: list[str] = []
        for dim_key, dim_name in (
            ("climate_consumption", "气候-消费带"),
            ("fragrance_consumption", "香氛消费"),
            ("fashion_fragrance_map", "穿搭风格-香调"),
            ("lifestyle_scenario", "生活方式"),
        ):
            dim_data = getattr(report, dim_key)
            if isinstance(dim_data, dict):
                summary = dim_data.get("summary")
                if summary:
                    fan_summaries.append(f"{dim_name}: {summary}")
        if fan_summaries:
            parts.append("【粉丝画像维度摘要】\n" + "\n".join(fan_summaries))

        return "\n".join(parts)

    # ---------- generate ----------

    async def generate(self, req: GenerateRequest) -> GenerateData:
        # 1. task 存在 + 已完成
        task = self._get_completed_task(req.task_id)

        # 2. 标签校验
        self._validate_tags(req.selected_tags)

        # 3. 读取 ProfileReport
        report = self._get_report(req.task_id)

        # 4. 权重归一化
        bw, aw, warnings = self._normalize_weights(
            req.blogger_weight, req.audience_weight
        )

        # 5. 融合画像
        fused_profile = self._build_fused_profile(req.task_id, report, bw, aw)

        # 6. 创建 session（generating 态先落库）+ task 标记为「调香推荐中」
        #    task 从 completed → processing，让前端 Dashboard 把它从「历史记录」
        #    提到「进行中」，用户能感知香调正在生成。progress 回退到 90 表示
        #    「画像分析已完成、调香进行中」，避免进度条显示满格像已到底。
        task.status = "processing"
        task.current_step = "正在生成香调方案"
        task.progress = 90
        self.db.add(task)
        session = FragranceSession(
            id=str(uuid.uuid4()),
            task_id=req.task_id,
            user_id=None,
            selected_tags=req.selected_tags,
            recommendations={
                "iceberg_analysis": {"surface": "", "middle": "", "deep": ""},
                "recommendations": [],
            },
            status=SESSION_STATUS_GENERATING,
            created_at=_now(),
            updated_at=_now(),
        )
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)

        # 7. 调引擎（含 1 次 JSON 解析重试）
        try:
            result = await self.engine.generate(
                fused_profile=fused_profile,
                selected_tags=req.selected_tags,
                plan_count=req.plan_count,
            )
            # 解析失败信号：recommendations 为空
            if not result.get("recommendations"):
                logger.warning(
                    f"generate: empty recommendations for session {session.id}, "
                    f"retrying once"
                )
                result = await self.engine.generate(
                    fused_profile=fused_profile + "\n\n（注意：上次输出无法解析，请严格返回 JSON 格式）",
                    selected_tags=req.selected_tags,
                    plan_count=req.plan_count,
                )
            if not result.get("recommendations"):
                raise FragranceEngineError(
                    "AI returned unparseable recommendations after retry"
                )
        except FragranceEngineError:
            self._mark_session_error(session)
            self._restore_task_completed(task)
            raise
        except Exception as e:
            logger.exception(f"generate: engine failure for session {session.id}")
            self._mark_session_error(session)
            self._restore_task_completed(task)
            raise FragranceEngineError(f"Fragrance engine failed: {e}") from e

        # 8. 持久化结果 + task 恢复 completed
        session.recommendations = {
            "iceberg_analysis": result.get("iceberg_analysis") or {
                "surface": "",
                "middle": "",
                "deep": "",
            },
            "recommendations": result.get("recommendations") or [],
        }
        session.status = SESSION_STATUS_COMPLETED
        session.updated_at = _now()
        task.status = "completed"
        task.current_step = "分析完成"
        task.progress = 100
        self.db.commit()

        # 9. 初始 assistant 消息（§2.1 业务逻辑 + §2.5 history msg_1）
        initial_msg = ChatMessage(
            id=str(uuid.uuid4()),
            session_id=session.id,
            role="assistant",
            content=INITIAL_ASSISTANT_MESSAGE.format(plan_count=req.plan_count),
            updated_plans=None,
            created_at=_now(),
        )
        self.db.add(initial_msg)
        self.db.commit()

        return self._build_generate_data(session, warnings)

    # ---------- chat ----------

    async def chat(self, session_id: str, message: str) -> ChatData:
        session = self._get_session(session_id)
        if session.status == SESSION_STATUS_ERROR:
            raise SessionStateError("Session is in error state, chat unavailable")

        # 取最近 MAX_HISTORY 条消息（滑窗）
        from app.engines.prompt_engine import MAX_HISTORY_MESSAGES

        db_msgs = (
            self.db.query(ChatMessage)
            .filter(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at.asc())
            .all()
        )
        history = [
            {"role": m.role, "content": m.content}
            for m in db_msgs[-MAX_HISTORY_MESSAGES:]
        ]

        # 先落库 user 消息（对称性：user 先写，AI 失败也保留痕迹）
        user_msg = ChatMessage(
            id=str(uuid.uuid4()),
            session_id=session_id,
            role="user",
            content=message,
            updated_plans=None,
            created_at=_now(),
        )
        self.db.add(user_msg)
        self.db.commit()

        current_plans = (session.recommendations or {}).get("recommendations", [])
        selected_tags = session.selected_tags or {}

        try:
            reply, updated_plans = await self.engine.chat(
                history=history,
                current_plans=current_plans,
                user_message=message,
                selected_tags=selected_tags,
            )
        except Exception as e:
            logger.exception(f"chat: engine failure for session {session_id}")
            raise FragranceEngineError(f"Fragrance chat engine failed: {e}") from e

        # 合并 updated_plans 到 session.recommendations（按 plan_id 替换）
        merged_plans = current_plans
        if updated_plans:
            merged_plans = self._merge_plans(current_plans, updated_plans)
            session.recommendations = {
                **(session.recommendations or {}),
                "recommendations": merged_plans,
            }
            session.updated_at = _now()
            self.db.commit()

        # 写 assistant 消息
        assistant_msg = ChatMessage(
            id=str(uuid.uuid4()),
            session_id=session_id,
            role="assistant",
            content=reply,
            updated_plans=updated_plans,
            created_at=_now(),
        )
        self.db.add(assistant_msg)
        self.db.commit()
        self.db.refresh(assistant_msg)

        return ChatData(
            reply=reply,
            updated_plans=[FragrancePlan(**p) for p in updated_plans] if updated_plans else None,
            message_id=assistant_msg.id,
        )

    # ---------- regenerate ----------

    async def regenerate(self, session_id: str, req: RegenerateRequest) -> GenerateData:
        session = self._get_session(session_id)
        if session.status == SESSION_STATUS_ERROR:
            raise SessionStateError("Session is in error state, regenerate unavailable")

        selected_tags = req.selected_tags or session.selected_tags or {}
        self._validate_tags(selected_tags)

        task = self._get_completed_task(session.task_id)
        report = self._get_report(session.task_id)

        bw, aw, warnings = self._normalize_weights(
            req.blogger_weight, req.audience_weight
        )
        fused_profile = self._build_fused_profile(session.task_id, report, bw, aw)

        # session 与 task 同步进入生成态（task → processing），让前端 Dashboard
        # 把任务从「历史记录」提到「进行中」，工坊页也能据此显示等待动画。
        # progress 回退到 90 表示「调香进行中」，避免进度条显示满格。
        session.status = SESSION_STATUS_GENERATING
        session.updated_at = _now()
        task.status = "processing"
        task.current_step = "正在重新生成香调方案"
        task.progress = 90
        self.db.add(task)
        self.db.commit()

        try:
            result = await self.engine.generate(
                fused_profile=fused_profile,
                selected_tags=selected_tags,
                plan_count=req.plan_count,
            )
            if not result.get("recommendations"):
                result = await self.engine.generate(
                    fused_profile=fused_profile + "\n\n（注意：上次输出无法解析，请严格返回 JSON 格式）",
                    selected_tags=selected_tags,
                    plan_count=req.plan_count,
                )
            if not result.get("recommendations"):
                raise FragranceEngineError(
                    "AI returned unparseable recommendations after retry"
                )
        except FragranceEngineError:
            self._mark_session_error(session)
            self._restore_task_completed(task)
            raise
        except Exception as e:
            logger.exception(f"regenerate: engine failure for session {session_id}")
            self._mark_session_error(session)
            self._restore_task_completed(task)
            raise FragranceEngineError(f"Fragrance engine failed: {e}") from e

        # 覆盖方案与标签 + task 恢复 completed
        session.selected_tags = selected_tags
        session.recommendations = {
            "iceberg_analysis": result.get("iceberg_analysis") or {
                "surface": "",
                "middle": "",
                "deep": "",
            },
            "recommendations": result.get("recommendations") or [],
        }
        session.status = SESSION_STATUS_COMPLETED
        session.updated_at = _now()
        task.status = "completed"
        task.current_step = "分析完成"
        task.progress = 100

        # 清空旧 chat 历史（方案变了，旧对话不再相关）
        self.db.query(ChatMessage).filter(
            ChatMessage.session_id == session_id
        ).delete(synchronize_session=False)

        self.db.commit()

        # 写一条新的初始 assistant 消息
        initial_msg = ChatMessage(
            id=str(uuid.uuid4()),
            session_id=session_id,
            role="assistant",
            content=INITIAL_ASSISTANT_MESSAGE.format(plan_count=req.plan_count),
            updated_plans=None,
            created_at=_now(),
        )
        self.db.add(initial_msg)
        self.db.commit()

        return self._build_generate_data(session, warnings)

    # ---------- read ----------

    def get_session_detail(self, session_id: str) -> SessionDetailData:
        session = self._get_session(session_id)
        recs = session.recommendations or {}
        iceberg = recs.get("iceberg_analysis") or {}
        plans = recs.get("recommendations") or []
        return SessionDetailData(
            session_id=session.id,
            task_id=session.task_id,
            selected_tags=session.selected_tags or {},
            iceberg_analysis=IcebergAnalysis(**iceberg) if isinstance(iceberg, dict) else IcebergAnalysis(),
            recommendations=[FragrancePlan(**p) for p in plans if isinstance(p, dict)],
            status=session.status,
            created_at=session.created_at,
        )

    def get_history(self, session_id: str) -> ChatHistoryData:
        # 先校验 session 存在
        self._get_session(session_id)
        msgs = (
            self.db.query(ChatMessage)
            .filter(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at.asc())
            .all()
        )
        items: list[ChatMessageItem] = []
        for m in msgs:
            updated = m.updated_plans if isinstance(m.updated_plans, list) else None
            items.append(
                ChatMessageItem(
                    id=m.id,
                    role=m.role,
                    content=m.content,
                    updated_plans=[FragrancePlan(**p) for p in updated] if updated else None,
                    created_at=m.created_at,
                )
            )
        return ChatHistoryData(messages=items)

    # ---------- 内部 helpers ----------

    def _get_session(self, session_id: str) -> FragranceSession:
        session = (
            self.db.query(FragranceSession)
            .filter(FragranceSession.id == session_id)
            .first()
        )
        if not session:
            raise SessionNotFoundError(f"Fragrance session not found: {session_id}")
        return session

    def _get_completed_task(self, task_id: str) -> AnalysisTask:
        task = (
            self.db.query(AnalysisTask)
            .filter(AnalysisTask.id == task_id)
            .first()
        )
        if not task:
            raise TaskNotFoundError(f"Task not found: {task_id}")
        if task.status != "completed":
            raise TaskNotCompletedError(
                f"Analysis task is not completed (current status: {task.status})"
            )
        return task

    def _get_report(self, task_id: str) -> ProfileReport:
        report = (
            self.db.query(ProfileReport)
            .filter(ProfileReport.task_id == task_id)
            .first()
        )
        if not report:
            raise TaskNotCompletedError("Profile report not generated for this task")
        return report

    def _mark_session_error(self, session: FragranceSession) -> None:
        try:
            session.status = SESSION_STATUS_ERROR
            session.updated_at = _now()
            self.db.commit()
        except Exception:  # noqa: BLE001
            logger.exception("Failed to mark session as error")

    def _restore_task_completed(self, task: AnalysisTask) -> None:
        """生成/重新生成失败时把 task 从 processing 恢复成 completed，
        否则任务会永远卡在「调香推荐中」，用户无法重试。"""
        try:
            task.status = "completed"
            task.current_step = "分析完成"
            task.progress = 100
            self.db.commit()
        except Exception:  # noqa: BLE001
            logger.exception("Failed to restore task status to completed")

    @staticmethod
    def _merge_plans(
        current: list[dict], updates: list[dict]
    ) -> list[dict]:
        """按 plan_id 合并：用 updates 中的方案替换 current 中同 id 的方案。"""
        update_map = {p.get("plan_id"): p for p in updates if isinstance(p, dict)}
        merged: list[dict] = []
        for plan in current:
            pid = plan.get("plan_id") if isinstance(plan, dict) else None
            if pid in update_map:
                merged.append(update_map.pop(pid))
            else:
                merged.append(plan)
        # 追加 updates 中新增的 plan_id（理论上不应出现，但防御性处理）
        merged.extend(update_map.values())
        return merged

    def _build_generate_data(
        self, session: FragranceSession, warnings: list[str]
    ) -> GenerateData:
        recs = session.recommendations or {}
        iceberg = recs.get("iceberg_analysis") or {}
        plans = recs.get("recommendations") or []
        return GenerateData(
            session_id=session.id,
            status=session.status,
            iceberg_analysis=IcebergAnalysis(**iceberg) if isinstance(iceberg, dict) else IcebergAnalysis(),
            recommendations=[FragrancePlan(**p) for p in plans if isinstance(p, dict)],
            warnings=warnings,
        )
