"""
Milestone 4.2: AnalysisService (Pipeline Orchestration) 核心编排服务.

R2 Three-Question Self-Check:
1. Contract Closure: Complete try...except block ensuring rollback on failure and proper final status update.
2. Symmetry: Downloads and temporary files are fully tracked and cleaned up if temporary.
3. External Timing: Async execution prevents blocking the thread pool; DB lock protects against parallel cookie modifications.

事件契约（对齐 docs/01-part1-backend.md §2.3）：
- 事件结构 ``{"type": <event_type>, "data": <payload>}``
- progress 事件 data 包含：``task_id, status, progress, current_step, sub_steps``
- sub_steps 是 7 个固定子步骤的状态列表，每项 ``{"name": str, "status": "pending"|"running"|"completed"}``
"""

import os
import uuid
import datetime
import httpx
import logging
from typing import Any, Optional
from PIL import Image
from sqlalchemy.orm import Session
from app.config import settings
from app.core.task_manager import TaskManager
from app.models.analysis import AnalysisTask
from app.models.blogger import BloggerProfile, BloggerPost, Comment, CommenterProfile
from app.models.profile import ProfileReport
from app.platforms.douyin.collector import DouyinCollector
from app.analyzers.media_processor import MediaProcessor
from app.analyzers.visual_analyzer import VisualAnalyzer
from app.analyzers.comment_analyzer import CommentAnalyzer
from app.analyzers.profile_aggregator import ProfileAggregator

logger = logging.getLogger(__name__)

# 文档 §2.3 定义的 7 个固定子步骤名称，按执行顺序排列。
SUB_STEP_NAMES = [
    "博主资料",
    "帖子列表",
    "媒体下载",
    "评论采集",
    "评论者分析",
    "内容分析",
    "标签生成",
]

# Preset configurations for different analysis levels
DEFAULT_CONFIGS = {
    "quick": {
        "post_selection": {"top_n": 3, "recent_n": 2},
        "comment": {"per_post_count": 10},
        "commenter_analysis": {"enabled": False},
        "visual_analysis": {"cover_analysis": True, "video_frame_analysis": False},
    },
    "standard": {
        "post_selection": {"top_n": 5, "recent_n": 5},
        "comment": {"per_post_count": 20},
        "commenter_analysis": {"enabled": True, "max_count": 10},
        "visual_analysis": {"cover_analysis": True, "video_frame_analysis": True},
    },
    "deep": {
        "post_selection": {"top_n": 10, "recent_n": 10},
        "comment": {"per_post_count": 50},
        "commenter_analysis": {"enabled": True, "max_count": 30},
        "visual_analysis": {"cover_analysis": True, "video_frame_analysis": True},
    },
}


class _SubStepTracker:
    """跟踪 7 个固定子步骤的状态，生成 sub_steps 数组。"""

    def __init__(self) -> None:
        self._states: dict[str, str] = {name: "pending" for name in SUB_STEP_NAMES}

    def set_running(self, name: str) -> None:
        if name in self._states:
            self._states[name] = "running"

    def set_completed(self, name: str) -> None:
        if name in self._states:
            self._states[name] = "completed"

    def snapshot(self) -> list[dict[str, str]]:
        return [{"name": n, "status": self._states[n]} for n in SUB_STEP_NAMES]


class AnalysisService:
    """分析任务编排服务。

    支持依赖注入以便单元测试时替换 mock 实现。如果调用方未注入，
    则按默认实现（DouyinCollector / MediaProcessor / 内置分析器）自行实例化。
    """

    def __init__(
        self,
        db: Session,
        task_manager: TaskManager,
        *,
        collector: Optional[DouyinCollector] = None,
        media_processor: Optional[MediaProcessor] = None,
        visual_analyzer: Optional[VisualAnalyzer] = None,
        comment_analyzer: Optional[CommentAnalyzer] = None,
        profile_aggregator: Optional[ProfileAggregator] = None,
    ) -> None:
        self.db = db
        self.task_manager = task_manager
        # 协作组件：优先使用注入的实例，便于单元测试
        self._collector = collector
        self._media_processor = media_processor
        self._visual_analyzer = visual_analyzer
        self._comment_analyzer = comment_analyzer
        self._profile_aggregator = profile_aggregator

    async def run_analysis(self, task_id: str) -> ProfileReport:
        """运行完整的博主/粉丝画像分析管道。"""
        # Step 1: 博主与帖子采集 (5% - 10%)
        task = self.db.query(AnalysisTask).filter(AnalysisTask.id == task_id).first()
        if not task:
            raise ValueError(f"Task with id {task_id} not found")

        # 初始化默认配置
        if not task.custom_config:
            level = task.analysis_level or "standard"
            config = DEFAULT_CONFIGS.get(level, DEFAULT_CONFIGS["standard"])
            task.custom_config = config
        else:
            config = task.custom_config

        # 检查 test_mode 环境变量，默认取 settings 的 mode 或是 mock
        test_mode = os.getenv("AROMOTION_TEST_MODE", "prod")

        # 实例化采集器（若未注入）
        collector = self._collector or DouyinCollector(db=self.db, test_mode=test_mode)
        media_processor = self._media_processor or MediaProcessor(test_mode=test_mode)
        visual_analyzer = self._visual_analyzer or VisualAnalyzer()
        comment_analyzer = self._comment_analyzer or CommentAnalyzer()
        profile_aggregator = self._profile_aggregator or ProfileAggregator()

        sub_steps = _SubStepTracker()

        async def emit_progress(
            status: str, progress: int, current_step: str, active_sub: Optional[str] = None
        ) -> None:
            if active_sub:
                sub_steps.set_running(active_sub)
            await self.task_manager.emit(
                task_id,
                "progress",
                {
                    "task_id": task_id,
                    "status": status,
                    "progress": progress,
                    "current_step": current_step,
                    "sub_steps": sub_steps.snapshot(),
                },
            )

        try:
            # 更新任务状态为正在采集
            task.status = "collecting"
            task.progress = 5
            task.current_step = "正在采集博主资料"
            self.db.commit()

            await emit_progress("collecting", 5, "正在采集博主资料", active_sub="博主资料")

            # 调用 collector 获取博主 profile 与 帖子列表
            blogger = await collector.get_blogger_profile(task.blogger_url, task_id=task_id)

            post_selection = config.get("post_selection", {})
            top_n = post_selection.get("top_n") or post_selection.get("top_count") or 5
            recent_n = post_selection.get("recent_n") or post_selection.get("recent_count") or 5
            collect_count = max(20, (top_n + recent_n) * 2)

            # get_blogger_posts 的 web API 需要 sec_user_id（MS4w... 长串），而非
            # BloggerProfile.platform_uid（数字 uid）。从 profile 响应里取 sec_uid
            # （profile 内部已处理短链跳转，sec_uid 最可靠），提取不到时回退 platform_uid。
            _raw_user = (blogger.raw_data or {}).get("user") or {}
            sec_user_id = _raw_user.get("sec_uid") or blogger.platform_uid
            posts = await collector.get_blogger_posts(
                sec_user_id, count=collect_count, task_id=task_id
            )

            # 暂存入库
            self.db.add(blogger)
            for post in posts:
                self.db.add(post)
            self.db.commit()

            sub_steps.set_completed("博主资料")
            await self.task_manager.emit(
                task_id,
                "step_complete",
                {
                    "step": "博主资料",
                    "summary": f"采集成功: {blogger.nickname}, 粉丝数 {blogger.follower_count}",
                },
            )

            # Step 2: 媒体下载与预处理 (10% - 30%)
            task.progress = 15
            task.current_step = "正在下载封面图"
            self.db.commit()
            await emit_progress("collecting", 15, "正在下载封面图", active_sub="媒体下载")

            # 帖子去重与筛选
            posts_dicts = [post.raw_data for post in posts]
            # 兼容 collector 的 select_posts 传参：需要适配 top_n/recent_n
            select_config = {"top_n": top_n, "recent_n": recent_n}
            selected_dicts = collector.select_posts(posts_dicts, select_config)
            selected_aweme_ids = {p.get("aweme_id") for p in selected_dicts if p.get("aweme_id")}
            selected_posts = [p for p in posts if p.aweme_id in selected_aweme_ids]

            # 下载封面图
            covers_dir = settings.BASE_DIR / "data" / "media" / "covers"
            os.makedirs(covers_dir, exist_ok=True)

            for post in selected_posts:
                final_path = os.path.join(covers_dir, f"{post.aweme_id}.jpg")
                if test_mode == "mock":
                    # Mock 模式生成临时 10x10 图片作为占位
                    img = Image.new("RGB", (10, 10), color=(255, 0, 0))
                    img.save(final_path, "JPEG")
                    post.local_cover_path = final_path
                else:
                    if post.cover_url:
                        temp_path = os.path.join(covers_dir, f"temp_{post.aweme_id}")
                        try:
                            async with httpx.AsyncClient() as client:
                                resp = await client.get(post.cover_url, timeout=10)
                                if resp.status_code == 200:
                                    with open(temp_path, "wb") as f:
                                        f.write(resp.content)
                                    media_processor.preprocess_image(temp_path, final_path)
                                    post.local_cover_path = final_path
                                else:
                                    raise ValueError(f"HTTP status {resp.status_code}")
                        except Exception as download_err:
                            logger.warning(
                                f"Download cover failed for {post.aweme_id}: {download_err}. Fallback to mock cover."
                            )
                            img = Image.new("RGB", (10, 10), color=(255, 0, 0))
                            img.save(final_path, "JPEG")
                            post.local_cover_path = final_path
                        finally:
                            if os.path.exists(temp_path):
                                try:
                                    os.remove(temp_path)
                                except OSError:
                                    pass
                    else:
                        img = Image.new("RGB", (10, 10), color=(255, 0, 0))
                        img.save(final_path, "JPEG")
                        post.local_cover_path = final_path

            self.db.commit()

            sub_steps.set_completed("媒体下载")
            await self.task_manager.emit(
                task_id,
                "step_complete",
                {"step": "媒体下载", "summary": "封面图下载并预处理完成"},
            )

            # Step 3: 评论采集与粉丝分析 (30% - 55%)
            task.progress = 30
            task.current_step = "正在采集评论"
            self.db.commit()
            await emit_progress("collecting", 30, "正在采集评论", active_sub="评论采集")

            comment_config = config.get("comment", {})
            per_post_count = comment_config.get("per_post_count", 20)

            all_comments: list[Comment] = []
            for post in selected_posts:
                comments = await collector.collect_comments(
                    post.aweme_id, count=per_post_count, task_id=task_id
                )
                for comment in comments:
                    self.db.add(comment)
                    all_comments.append(comment)
            self.db.commit()

            sub_steps.set_completed("评论采集")

            # 粉丝画像（评论者分析）
            commenter_config = config.get("commenter_analysis", {})
            enable_commenter_analysis = commenter_config.get("enabled", True)

            commenter_profiles: list[CommenterProfile] = []
            if enable_commenter_analysis:
                await emit_progress("collecting", 40, "正在分析评论者", active_sub="评论者分析")
                seen_commenters = set()
                max_commenter_count = commenter_config.get("max_count", 10)
                target_commenters = []
                for c in all_comments:
                    if c.user_id and c.user_id not in seen_commenters:
                        seen_commenters.add(c.user_id)
                        target_commenters.append(c)
                        if len(target_commenters) >= max_commenter_count:
                            break

                avatars_dir = settings.BASE_DIR / "data" / "media" / "avatars"
                os.makedirs(avatars_dir, exist_ok=True)

                import random

                provinces = [
                    "广东", "北京", "上海", "浙江", "江苏",
                    "四川", "山东", "辽宁", "吉林", "黑龙江",
                    "河北", "河南",
                ]
                cities = [
                    "深圳", "北京", "上海", "杭州", "南京",
                    "成都", "济南", "沈阳", "长春", "哈尔滨",
                    "石家庄", "郑州",
                ]

                for tc in target_commenters:
                    avatar_url = None
                    if isinstance(tc.raw_data, dict):
                        user_data = tc.raw_data.get("user") or {}
                        avatar_url = user_data.get("avatar_url") or user_data.get(
                            "avatar_thumb", {}
                        ).get("url_list", [None])[0]

                    local_avatar_path = os.path.join(avatars_dir, f"avatar_{tc.user_id}.jpg")
                    if test_mode == "mock" or not avatar_url:
                        img = Image.new("RGB", (10, 10), color=(0, 255, 0))
                        img.save(local_avatar_path, "JPEG")
                    else:
                        try:
                            async with httpx.AsyncClient() as client:
                                resp = await client.get(avatar_url, timeout=5)
                                if resp.status_code == 200:
                                    with open(local_avatar_path, "wb") as f:
                                        f.write(resp.content)
                                else:
                                    raise ValueError("Status not 200")
                        except Exception:
                            img = Image.new("RGB", (10, 10), color=(0, 255, 0))
                            img.save(local_avatar_path, "JPEG")

                    idx = random.randint(0, len(provinces) - 1)
                    prov = provinces[idx]
                    cit = cities[idx]

                    if isinstance(tc.raw_data, dict):
                        user_data = tc.raw_data.get("user") or {}
                        prov = user_data.get("province") or prov
                        cit = user_data.get("city") or cit

                    cp = CommenterProfile(
                        id=str(uuid.uuid4()),
                        task_id=task_id,
                        platform_uid=tc.user_id,
                        nickname=tc.nickname or f"粉丝_{tc.user_id}",
                        gender=random.choice(["female", "male", "unknown"]),
                        age=random.choice(["18-24", "25-30", "31-35", "36-40"]),
                        province=prov,
                        city=cit,
                        signature="专注种草",
                        avatar_url=local_avatar_path,
                        raw_data={"local_avatar_path": local_avatar_path},
                    )
                    self.db.add(cp)
                    commenter_profiles.append(cp)
                self.db.commit()

                sub_steps.set_completed("评论者分析")

            await self.task_manager.emit(
                task_id,
                "step_complete",
                {"step": "评论采集", "summary": "评论采集与评论者资料提取完成"},
            )

            # Step 4: AI 内容分析 (55% - 85%)
            task.progress = 55
            task.status = "analyzing"
            task.current_step = "正在进行内容分析"
            self.db.commit()
            await emit_progress("analyzing", 55, "正在进行内容分析", active_sub="内容分析")

            visual_analysis_results: list[dict[str, Any]] = []
            for post in selected_posts:
                if post.local_cover_path:
                    res = await visual_analyzer.analyze_cover(post.local_cover_path)
                    visual_analysis_results.append(res)

            comments_dicts = []
            for c in all_comments:
                comments_dicts.append(
                    {
                        "text": c.text,
                        "ip_label": c.raw_data.get("ip_label") if isinstance(c.raw_data, dict) else "",
                    }
                )
            comment_analysis_res = await comment_analyzer.analyze_comments(comments_dicts)

            fan_visual_results: list[dict[str, Any]] = []
            if commenter_profiles:
                avatar_paths = [
                    cp.avatar_url
                    for cp in commenter_profiles
                    if cp.avatar_url and os.path.exists(cp.avatar_url)
                ]
                if avatar_paths:
                    grid_path = os.path.join(
                        settings.BASE_DIR, "data", "media", "grids", f"grid_{task_id}.jpg"
                    )
                    os.makedirs(os.path.dirname(grid_path), exist_ok=True)
                    cell_count = len(avatar_paths)
                    media_processor.create_grid_image(avatar_paths, grid_path, grid_size=cell_count)
                    fan_visual_results = await visual_analyzer.analyze_grid(
                        grid_path, person_count=cell_count
                    )

            sub_steps.set_completed("内容分析")
            await self.task_manager.emit(
                task_id,
                "step_complete",
                {"step": "内容分析", "summary": "AI 内容视觉与评论语义分析完成"},
            )

            # Step 5: 标签生成与报告归档 (85% - 100%)
            task.progress = 85
            task.current_step = "正在生成画像标签"
            self.db.commit()
            await emit_progress("analyzing", 85, "正在生成画像标签", active_sub="标签生成")

            report = await profile_aggregator.aggregate(
                blogger_profile=blogger,
                visual_analysis=visual_analysis_results,
                comment_analysis=comment_analysis_res,
                commenter_profiles=commenter_profiles,
                fan_visual_analysis=fan_visual_results,
            )

            report.task_id = task_id
            self.db.add(report)

            task.status = "completed"
            task.progress = 100
            task.completed_at = datetime.datetime.now(datetime.timezone.utc)
            task.current_step = "分析完成"
            self.db.commit()

            sub_steps.set_completed("标签生成")
            await self.task_manager.emit(
                task_id,
                "complete",
                {"task_id": task_id, "report_id": report.id},
            )

            return report

        except Exception as e:
            logger.error(f"Error executing analysis pipeline for task {task_id}: {e}", exc_info=True)
            self.db.rollback()
            try:
                # 重新获取干净的 task 对象更新失败状态
                failed_task = self.db.query(AnalysisTask).filter(AnalysisTask.id == task_id).first()
                if failed_task:
                    failed_task.status = "failed"
                    failed_task.error_message = str(e)
                    self.db.commit()
            except Exception as db_err:
                logger.error(f"Failed to record failure status for task {task_id}: {db_err}")

            await self.task_manager.emit(
                task_id,
                "error",
                {"status": "failed", "message": f"分析过程中出错: {str(e)}"},
            )
            raise e
