"""
TaskService: 分析任务的 CRUD 业务层 (Part1 §2)。

封装 AnalysisTask 的创建、查询、取消、删除、报告/标签获取等纯数据库操作，
将 HTTP 层与 TaskManager / AnalysisService 解耦。重逻辑（pipeline 执行）
仍在 AnalysisService 中。

R2 Three-Question Self-Check:
1. Contract Closure: 每个方法对应文档 §2.x 的一个接口契约；状态流转、错误
   形态都有明确的异常类型，由 API 层捕获并转换为 HTTP 状态码。
2. Symmetry: create/get/delete 严格对称；delete_task 在删除数据库记录前
   清理关联媒体文件；状态机闭环 (pending -> collecting -> analyzing ->
   completed|failed|cancelled)。
3. External Timing: 所有写操作均通过单次 db.commit 提交；运行中任务的取消
   先调用 task_manager.cancel 再更新数据库状态，避免异步任务仍在写入。
"""

import os
import uuid
import shutil
import datetime
import logging
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.config import settings
from app.core.task_manager import TaskManager
from app.models.analysis import AnalysisTask
from app.models.blogger import BloggerProfile, BloggerPost, CommenterProfile
from app.models.profile import ProfileReport
from app.models.fragrance import FragranceSession
from app.services.cookie_service import CookieService

logger = logging.getLogger(__name__)

SUPPORTED_PLATFORMS = {"douyin", "xiaohongshu", "taobao"}
PRESET_LEVELS = {"quick", "standard", "deep"}

# 平台域名 -> 平台标识，用于 URL 自动识别
PLATFORM_DOMAINS: dict[str, tuple[str, ...]] = {
    "douyin": ("douyin.com", "iesdouyin.com"),
    "xiaohongshu": ("xiaohongshu.com", "xhslink.com"),
    "taobao": ("taobao.com",),
}

# 文档 §9 维度名称映射
DIMENSION_NAMES: dict[str, str] = {
    "climate_consumption": "气候-消费带",
    "fragrance_consumption": "香氛消费",
    "fashion_fragrance_map": "穿搭风格-香调映射",
    "lifestyle_scenario": "生活方式场景",
}

SUB_DIMENSION_NAMES: dict[str, dict[str, str]] = {
    "climate_consumption": {
        "climate_zone": "气候带",
        "city_tier": "城市线级",
        "culture_circle": "文化圈",
        "concentration": "集中度",
    },
    "fragrance_consumption": {
        "price_tier": "价格档次",
        "purchase_motivation": "购买动机",
        "decision_path": "决策路径",
        "consumption_frequency": "消费频率",
    },
    "fashion_fragrance_map": {
        "fashion_style": "穿搭风格",
        "fashion_scene": "时尚场景",
        "color_preference": "颜色偏好",
        "fashion_completeness": "时尚完整度",
    },
    "lifestyle_scenario": {
        "core_interest": "核心兴趣",
        "social_activity": "社交活动",
        "aesthetic_personality": "审美个性",
        "fragrance_timing": "香水使用时机",
        "content_consumption": "内容消费",
    },
}

# 文档 §9.2 互斥标签组：dimension_id -> {sub_id -> group_name}
MUTUALLY_EXCLUSIVE_GROUPS: dict[str, dict[str, str]] = {
    "climate_consumption": {
        "climate_zone": "climate",
    },
}


def _to_float(value) -> float:
    """容忍 None / 字符串 / int / float 的安全转换。"""
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


# 自定义异常：API 层据此返回明确的 HTTP 状态码
class TaskNotFoundError(KeyError):
    """任务不存在 (HTTP 404)。"""


class TaskValidationError(ValueError):
    """请求参数非法 (HTTP 400 或 422)。"""


class TaskStateError(ValueError):
    """任务状态不允许此操作 (HTTP 400)。"""


class CookieRequiredError(PermissionError):
    """缺少有效 Cookie (HTTP 400)。"""


class ReportNotReadyError(PermissionError):
    """报告尚未生成 (HTTP 400)。"""


class TaskService:
    def __init__(
        self,
        db: Session,
        task_manager: TaskManager,
        cookie_service: CookieService,
    ) -> None:
        self.db = db
        self.task_manager = task_manager
        self.cookie_service = cookie_service

    # ---------- helpers ----------

    @staticmethod
    def _detect_platform(blogger_url: str) -> Optional[str]:
        for platform, domains in PLATFORM_DOMAINS.items():
            if any(d in blogger_url for d in domains):
                return platform
        return None

    @staticmethod
    def _validate_custom_config(custom_config: Optional[dict]) -> None:
        """对 custom_config 做边界校验 (§2.1 out-of-bounds 测试)。"""
        if not custom_config:
            raise TaskValidationError(
                "Custom configuration is required for custom analysis level"
            )
        ps = custom_config.get("post_selection", {}) or {}
        top_count = ps.get("top_count", 0)
        recent_count = ps.get("recent_count", 0)
        # 0..100 是文档 §2.1 test_f2_create_task_out_of_bounds_parameters 的边界
        for name, value in (("top_count", top_count), ("recent_count", recent_count)):
            if not isinstance(value, int) or value < 0 or value > 100:
                raise TaskValidationError(f"Parameter {name} out of bounds: {value}")

    # ---------- create ----------

    async def create_task(
        self,
        blogger_url: str,
        platform: str,
        analysis_level: str,
        custom_config: Optional[dict],
    ) -> AnalysisTask:
        # 1. URL 格式
        if not blogger_url or not blogger_url.startswith("http"):
            raise TaskValidationError("Invalid blogger URL format")

        # 2. 平台自动识别
        if platform == "auto" or not platform:
            platform = self._detect_platform(blogger_url) or "douyin"
        if platform not in SUPPORTED_PLATFORMS:
            raise TaskValidationError(f"Platform not supported: {platform}")

        # 3. Cookie 必须存在且有效
        cookie = await self.cookie_service.get_valid_cookie(self.db, platform)
        if not cookie:
            raise CookieRequiredError(
                f"Platform cookie is required and must be valid for {platform}"
            )

        # 4. 分析级别 / 自定义配置
        if analysis_level == "custom":
            self._validate_custom_config(custom_config)
        elif analysis_level not in PRESET_LEVELS:
            raise TaskValidationError(f"Unknown analysis level: {analysis_level}")

        # 5. 创建任务记录
        now = datetime.datetime.now(datetime.timezone.utc)
        task = AnalysisTask(
            id=str(uuid.uuid4()),
            platform=platform,
            blogger_url=blogger_url,
            analysis_level=analysis_level,
            custom_config=custom_config,
            status="pending",
            progress=0,
            current_step="准备开始",
            created_at=now,
            updated_at=now,
        )
        self.db.add(task)
        self.db.commit()
        self.db.refresh(task)
        return task

    # ---------- read ----------

    def get_task(self, task_id: str) -> AnalysisTask:
        task = self.db.query(AnalysisTask).filter(AnalysisTask.id == task_id).first()
        if not task:
            raise TaskNotFoundError(f"Task not found: {task_id}")
        return task

    def list_tasks(
        self, page: int = 1, page_size: int = 20, status: str = "all"
    ) -> tuple[list[AnalysisTask], int]:
        if page < 1:
            page = 1
        if page_size < 1 or page_size > 100:
            page_size = 20

        q = self.db.query(AnalysisTask)
        if status != "all":
            q = q.filter(AnalysisTask.status == status)
        total = q.count()
        items = (
            q.order_by(desc(AnalysisTask.created_at))
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        return items, total

    def has_fragrance_session(self, task_id: str) -> bool:
        return (
            self.db.query(FragranceSession)
            .filter(FragranceSession.task_id == task_id)
            .count()
            > 0
        )

    def get_fragrance_session_id(self, task_id: str) -> Optional[str]:
        """返回该 task 关联的香调 session id（取最新一个），无则 None。"""
        session = (
            self.db.query(FragranceSession)
            .filter(FragranceSession.task_id == task_id)
            .order_by(desc(FragranceSession.created_at))
            .first()
        )
        return session.id if session else None

    def get_blogger_info(self, task_id: str) -> Optional[BloggerProfile]:
        return (
            self.db.query(BloggerProfile)
            .filter(BloggerProfile.task_id == task_id)
            .first()
        )

    # ---------- cancel ----------

    async def cancel_task(self, task_id: str) -> AnalysisTask:
        task = self.get_task(task_id)
        if task.status == "completed":
            raise TaskStateError("Cannot cancel a completed task")
        if task.status in ("failed", "cancelled"):
            raise TaskStateError("Task is already terminated")

        # 若任务在 task_manager 中仍在运行，先取消以避免后续写入
        if self.task_manager.get_status(task_id) == "running":
            try:
                await self.task_manager.cancel(task_id)
            except Exception as e:  # noqa: BLE001
                logger.warning(f"task_manager.cancel failed for {task_id}: {e}")

        task.status = "cancelled"
        task.current_step = "已取消"
        task.updated_at = datetime.datetime.now(datetime.timezone.utc)
        self.db.commit()
        self.db.refresh(task)
        return task

    # ---------- report / tags ----------

    def get_report(self, task_id: str) -> tuple[AnalysisTask, ProfileReport]:
        task = self.get_task(task_id)
        # 文档 §2.4 + e2e: pending/collecting 时期访问 report 应 400
        if task.status in ("pending", "collecting"):
            raise ReportNotReadyError("Report is not generated yet")
        report = (
            self.db.query(ProfileReport)
            .filter(ProfileReport.task_id == task_id)
            .first()
        )
        if not report:
            raise ReportNotReadyError("Report is not generated yet")
        return task, report

    def get_report_for_tags(self, task_id: str) -> ProfileReport:
        task = self.get_task(task_id)
        if task.status == "failed":
            raise ReportNotReadyError("Tags unavailable for failed tasks")
        report = (
            self.db.query(ProfileReport)
            .filter(ProfileReport.task_id == task_id)
            .first()
        )
        if not report:
            raise ReportNotReadyError("Tags unavailable: report not generated")
        return report

    # ---------- tags taxonomy builder ----------

    def build_tags_dimensions(self, report: ProfileReport) -> list:
        """将 ProfileReport 的四维度 JSON 转换为前端标签结构（§2.5）。

        返回值为 ``app.schemas.analysis.Dimension`` 列表；为避免
        schemas 与 services 之间的循环引用，方法内部 import schema 类型。
        """
        from app.schemas.analysis import Dimension, SubDimension, TagItem

        raw_map = {
            "climate_consumption": report.climate_consumption,
            "fragrance_consumption": report.fragrance_consumption,
            "fashion_fragrance_map": report.fashion_fragrance_map,
            "lifestyle_scenario": report.lifestyle_scenario,
        }

        # 不参与标签筛选的字段（总结、集中度等字符串字段）
        NON_TAG_FIELDS = {"summary", "concentration", "overall_summary"}

        dimensions: list[Dimension] = []
        for dim_id, raw in raw_map.items():
            if not isinstance(raw, dict):
                continue
            sub_name_map = SUB_DIMENSION_NAMES.get(dim_id, {})
            mutex_map = MUTUALLY_EXCLUSIVE_GROUPS.get(dim_id, {})

            sub_dims: list[SubDimension] = []
            for sub_id, value in raw.items():
                if sub_id in NON_TAG_FIELDS:
                    continue
                if not isinstance(value, dict):
                    continue
                tags: list[TagItem] = []
                # 文档 §2.5：is_default_selected 自动选中比例最高的标签
                sorted_items = sorted(
                    value.items(),
                    key=lambda kv: (_to_float(kv[1]), kv[0]),
                    reverse=True,
                )
                for idx, (name, pct) in enumerate(sorted_items):
                    tags.append(
                        TagItem(
                            name=str(name),
                            percentage=_to_float(pct),
                            is_default_selected=(idx == 0),
                            mutually_exclusive_group=mutex_map.get(sub_id),
                        )
                    )
                sub_dims.append(
                    SubDimension(
                        sub_id=sub_id,
                        sub_name=sub_name_map.get(sub_id, sub_id),
                        tags=tags,
                        is_mutually_exclusive=bool(mutex_map.get(sub_id)),
                        max_select=1 if mutex_map.get(sub_id) else None,
                    )
                )

            dimensions.append(
                Dimension(
                    dimension_id=dim_id,
                    dimension_name=DIMENSION_NAMES.get(dim_id, dim_id),
                    sub_dimensions=sub_dims,
                )
            )
        return dimensions

    # ---------- delete ----------

    def delete_task(self, task_id: str) -> bool:
        task = self.get_task(task_id)
        if task.status in ("collecting", "analyzing"):
            raise TaskStateError("Cannot delete task mid-run")

        # 清理关联媒体文件 (covers / avatars / grids)
        self._cleanup_task_media(task_id)

        # 数据库级联删除（外键 ondelete=CASCADE）
        self.db.delete(task)
        self.db.commit()
        return True

    def _cleanup_task_media(self, task_id: str) -> None:
        """尽力清理任务关联的本地媒体文件。

        现有存储布局（AnalysisService）：
        - data/media/covers/{aweme_id}.jpg
        - data/media/avatars/avatar_{user_id}.jpg
        - data/media/grids/grid_{task_id}.jpg
        """
        media_base = settings.BASE_DIR / "data" / "media"
        try:
            # grids 直接按 task_id 命名
            grid_path = media_base / "grids" / f"grid_{task_id}.jpg"
            if grid_path.exists():
                grid_path.unlink()

            # 通过 posts 关联的封面
            posts = (
                self.db.query(BloggerPost)
                .filter(BloggerPost.task_id == task_id)
                .all()
            )
            for post in posts:
                if post.local_cover_path and os.path.exists(post.local_cover_path):
                    try:
                        os.remove(post.local_cover_path)
                    except OSError:
                        pass
                if post.local_video_path and os.path.exists(post.local_video_path):
                    try:
                        os.remove(post.local_video_path)
                    except OSError:
                        pass

            # 评论者头像
            commenters = (
                self.db.query(CommenterProfile)
                .filter(CommenterProfile.task_id == task_id)
                .all()
            )
            for cp in commenters:
                if cp.avatar_url and os.path.exists(cp.avatar_url):
                    try:
                        os.remove(cp.avatar_url)
                    except OSError:
                        pass
        except Exception as e:  # noqa: BLE001
            logger.warning(f"Media cleanup partially failed for task {task_id}: {e}")
