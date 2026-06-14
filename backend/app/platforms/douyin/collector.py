import os
import re
import json
import uuid
import datetime
import shutil
import asyncio
from sqlalchemy.orm import Session
from app.platforms.base import BaseCollector
from app.models.blogger import BloggerProfile, BloggerPost, Comment
from app.services.cookie_service import CookieService
from app.config import settings

class DouyinCollector(BaseCollector):
    # 类级别的 Lock，确保对同一个 db session 或者 cookie 读取在并发时是安全的
    _cookie_lock = asyncio.Lock()

    def __init__(self, db: Session = None, test_mode: str = None):
        self.db = db
        self.cookie_service = CookieService()
        # 允许通过环境变量或入参设定 test_mode
        self.test_mode = test_mode or os.getenv("AROMOTION_TEST_MODE", "prod")

    def _flatten_cookies(self, cookie_data: list[dict]) -> dict[str, str]:
        flattened = {}
        if not isinstance(cookie_data, list):
            return flattened
        for cookie in cookie_data:
            if cookie is None or not isinstance(cookie, dict):
                continue
            name = cookie.get("name")
            value = cookie.get("value")
            if name and value is not None:
                flattened[name] = str(value)
        return flattened

    async def _get_cookies(self) -> tuple[list[dict], dict[str, str]]:
        """
        获取 Cookie，支持 DB 读取与磁盘 Fallback 降级。
        使用 Lock 防范多任务并发时的 Cookie 读取冲突。
        """
        if self.db is None:
            # Fallback to local disk json if db is not provided
            cookie_dir = settings.COOKIE_DIR
            if not os.path.isabs(cookie_dir):
                cookie_dir = str((settings.BASE_DIR / cookie_dir).resolve())
            cookie_file = os.path.join(cookie_dir, "douyin.json")
            if os.path.exists(cookie_file):
                try:
                    with open(cookie_file, "r", encoding="utf-8") as f:
                        cookie_data = json.load(f)
                        return cookie_data, self._flatten_cookies(cookie_data)
                except Exception:
                    pass
            return [], {}

        async with self._cookie_lock:
            cookie_record = await self.cookie_service.get_valid_cookie(self.db, "douyin")
            if cookie_record and cookie_record.cookie_data:
                return cookie_record.cookie_data, self._flatten_cookies(cookie_record.cookie_data)
            return [], {}

    def _load_mock_data(self, filename: str) -> dict | list:
        # 查找 mock 数据，优先从 tests/mock_data，然后 tests/e2e/mock_data，最后如果都不存在则返回默认数据
        paths = [
            os.path.join(settings.BASE_DIR, "tests", "mock_data", filename),
            os.path.join(settings.BASE_DIR, "tests", "e2e", "mock_data", filename),
        ]
        for path in paths:
            if os.path.exists(path):
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        return json.load(f)
                except Exception:
                    pass
        # 默认内置 mock 数据以确保 100% 成功
        if "profile" in filename:
            return {
                "uid": "123456789",
                "nickname": "时尚博主A",
                "avatar_url": "https://p3.douyinpic.com/img/webcast/avatar1.jpg",
                "follower_count": 550000,
                "platform": "douyin",
                "description": "专注于都市轻奢穿搭与时尚美妆分享",
                "gender": "female",
                "city": "上海",
                "mcn_name": "时尚矩阵"
            }
        elif "comment" in filename:
            return [
                {
                    "cid": "comment_1",
                    "text": "这套粉色洛丽塔小裙子也太甜了吧！求求链接！",
                    "digg_count": 128,
                    "create_time": 1780000000,
                    "user": {
                        "uid": "fan_1",
                        "nickname": "粉色甜心",
                        "avatar_url": "https://avatar.url/1"
                    }
                }
            ]
        return {}

    async def get_blogger_profile(self, blogger_url: str, task_id: str = None) -> BloggerProfile:
        """
        获取博主基本信息 (主通道: curl_cffi)
        """
        # 提取 sec_user_id / 处理短链
        sec_user_id = blogger_url
        if "v.douyin.com" in blogger_url:
            if self.test_mode == "mock":
                sec_user_id = "mock_sec_user_id"
            else:
                try:
                    from curl_cffi.requests import AsyncSession
                    headers = {
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36"
                    }
                    async with AsyncSession() as session:
                        resp = await session.head(blogger_url, headers=headers, allow_redirects=True, timeout=10)
                        real_url = resp.url
                        match = re.search(r"user/([a-zA-Z0-9_-]+)", real_url)
                        if match:
                            sec_user_id = match.group(1)
                        else:
                            # 尝试解析 sec_uid 参数
                            match_query = re.search(r"sec_uid=([a-zA-Z0-9_-]+)", real_url)
                            if match_query:
                                sec_user_id = match_query.group(1)
                            else:
                                sec_user_id = real_url
                except Exception as e:
                    if self.test_mode != "mock":
                        raise e
        else:
            match = re.search(r"user/([a-zA-Z0-9_-]+)", blogger_url)
            sec_user_id = match.group(1) if match else blogger_url

        if self.test_mode == "mock":
            raw_data = self._load_mock_data("blogger_profile.json")
            # 兼容如果是 list 格式的话，取第一个
            if isinstance(raw_data, list) and len(raw_data) > 0:
                raw_data = raw_data[0]
            elif isinstance(raw_data, list):
                raw_data = {}
            return BloggerProfile(
                id=str(uuid.uuid4()),
                task_id=task_id or str(uuid.uuid4()),
                platform_uid=raw_data.get("uid") or raw_data.get("platform_uid") or "unknown",
                nickname=raw_data.get("nickname", "unknown"),
                gender=raw_data.get("gender"),
                age=raw_data.get("age"),
                province=raw_data.get("province"),
                city=raw_data.get("city"),
                signature=raw_data.get("description") or raw_data.get("signature"),
                follower_count=raw_data.get("follower_count", 0),
                following_count=raw_data.get("following_count", 0),
                total_favorited=raw_data.get("total_favorited", 0),
                aweme_count=raw_data.get("aweme_count", 0),
                avatar_url=raw_data.get("avatar_url"),
                raw_data=raw_data
            )

        # 真实请求
        try:
            from curl_cffi.requests import AsyncSession
            _, flattened_cookies = await self._get_cookies()
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36",
                "Referer": "https://www.douyin.com/"
            }
            url = f"https://www.douyin.com/aweme/v1/web/user/profile/other/?device_platform=webapp&aid=6383&source=channel_pc_web&sec_user_id={sec_user_id}"
            
            async with AsyncSession() as session:
                resp = await session.get(url, headers=headers, cookies=flattened_cookies, impersonate="chrome110", timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                user_info = data.get("user", {})
                if not user_info:
                    raise ValueError("No user info in response")
                return BloggerProfile(
                    id=str(uuid.uuid4()),
                    task_id=task_id or str(uuid.uuid4()),
                    platform_uid=user_info.get("uid", sec_user_id),
                    nickname=user_info.get("nickname", ""),
                    gender="female" if user_info.get("gender") == 2 else "male" if user_info.get("gender") == 1 else "unknown",
                    age=None,
                    province=user_info.get("province"),
                    city=user_info.get("city"),
                    signature=user_info.get("signature"),
                    follower_count=user_info.get("m_follower_count", 0) or user_info.get("follower_count", 0),
                    following_count=user_info.get("following_count", 0),
                    total_favorited=user_info.get("total_favorited", 0),
                    aweme_count=user_info.get("aweme_count", 0),
                    avatar_url=user_info.get("avatar_larger", {}).get("url_list", [None])[0] or user_info.get("avatar_thumb", {}).get("url_list", [None])[0],
                    raw_data=data
                )
            else:
                raise ValueError(f"HTTP status code: {resp.status_code}")
        except Exception as e:
            if self.test_mode != "mock":
                raise e
            # 优雅降级，当网络请求超时或出错时，退回使用 Mock 数据
            raw_data = self._load_mock_data("blogger_profile.json")
            if isinstance(raw_data, list) and len(raw_data) > 0:
                raw_data = raw_data[0]
            elif isinstance(raw_data, list):
                raw_data = {}
            return BloggerProfile(
                id=str(uuid.uuid4()),
                task_id=task_id or str(uuid.uuid4()),
                platform_uid=raw_data.get("uid") or raw_data.get("platform_uid") or sec_user_id,
                nickname=raw_data.get("nickname", "降级用户"),
                gender=raw_data.get("gender"),
                age=raw_data.get("age"),
                province=raw_data.get("province"),
                city=raw_data.get("city"),
                signature=raw_data.get("description") or raw_data.get("signature"),
                follower_count=raw_data.get("follower_count", 0),
                avatar_url=raw_data.get("avatar_url"),
                raw_data={"error": str(e), "fallback": True, **raw_data}
            )

    async def get_blogger_posts(self, blogger_uid: str, count: int, task_id: str = None) -> list[BloggerPost]:
        """
        获取博主帖子列表 (主通道: curl_cffi)
        """
        if self.test_mode == "mock":
            mock_posts = []
            for i in range(count):
                mock_posts.append(BloggerPost(
                    id=str(uuid.uuid4()),
                    task_id=task_id or str(uuid.uuid4()),
                    aweme_id=f"aweme_{i}",
                    title=f"Mock 帖子标题 {i}",
                    desc=f"Mock 帖子描述 {i}",
                    create_time=int(datetime.datetime.now().timestamp()) - i * 3600,
                    like_count=1000 - i * 100,
                    comment_count=100 - i * 10,
                    share_count=50 - i * 5,
                    cover_url="https://cover.url/mock",
                    video_url="https://video.url/mock",
                    raw_data={"aweme_id": f"aweme_{i}", "statistics": {"digg_count": 1000 - i * 100, "comment_count": 100 - i * 10, "share_count": 50 - i * 5}, "create_time": int(datetime.datetime.now().timestamp()) - i * 3600}
                ))
            return mock_posts

        try:
            from curl_cffi.requests import AsyncSession
            _, flattened_cookies = await self._get_cookies()
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36",
                "Referer": "https://www.douyin.com/"
            }
            url = f"https://www.douyin.com/aweme/v1/web/aweme/post/?device_platform=webapp&aid=6383&sec_user_id={blogger_uid}&count={count}"
            async with AsyncSession() as session:
                resp = await session.get(url, headers=headers, cookies=flattened_cookies, impersonate="chrome110", timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                aweme_list = data.get("aweme_list", []) or []
                posts = []
                for item in aweme_list:
                    stats = item.get("statistics") or {}
                    video = item.get("video") or {}
                    video_url = video.get("play_addr", {}).get("url_list", [None])[0]
                    cover_url = video.get("cover", {}).get("url_list", [None])[0]
                    posts.append(BloggerPost(
                        id=str(uuid.uuid4()),
                        task_id=task_id or str(uuid.uuid4()),
                        aweme_id=item.get("aweme_id"),
                        title=item.get("desc"),
                        desc=item.get("desc"),
                        create_time=item.get("create_time", 0),
                        like_count=stats.get("digg_count", 0) or 0,
                        comment_count=stats.get("comment_count", 0) or 0,
                        share_count=stats.get("share_count", 0) or 0,
                        cover_url=cover_url,
                        video_url=video_url,
                        raw_data=item
                    ))
                return posts
            else:
                raise ValueError(f"HTTP status code: {resp.status_code}")
        except Exception as e:
            if self.test_mode != "mock":
                raise e
            # 优雅降级到 Mock
            mock_posts = []
            for i in range(count):
                mock_posts.append(BloggerPost(
                    id=str(uuid.uuid4()),
                    task_id=task_id or str(uuid.uuid4()),
                    aweme_id=f"fallback_aweme_{i}",
                    title=f"降级帖子 {i}",
                    desc=f"降级帖子描述 {i}",
                    create_time=int(datetime.datetime.now().timestamp()) - i * 3600,
                    like_count=500 - i * 50,
                    comment_count=50 - i * 5,
                    share_count=20 - i * 2,
                    raw_data={"aweme_id": f"fallback_aweme_{i}", "error": str(e), "create_time": int(datetime.datetime.now().timestamp()) - i * 3600}
                ))
            return mock_posts

    async def collect_comments(self, post_id: str, count: int, task_id: str = None) -> list[Comment]:
        """
        获取评论列表 (辅助通道: Playwright)
        """
        if self.test_mode == "mock":
            raw_comments = self._load_mock_data("comments_list.json")
            # 兼容格式
            if not isinstance(raw_comments, list):
                raw_comments = []
            comments = []
            for item in raw_comments[:count]:
                user = item.get("user") or {}
                comments.append(Comment(
                    id=str(uuid.uuid4()),
                    task_id=task_id or str(uuid.uuid4()),
                    aweme_id=post_id,
                    cid=item.get("cid"),
                    user_id=user.get("uid"),
                    nickname=user.get("nickname"),
                    text=item.get("text"),
                    create_time=item.get("create_time", 0),
                    digg_count=item.get("digg_count", 0),
                    reply_comment_total=item.get("reply_comment_total", 0),
                    raw_data=item
                ))
            return comments

        # 真实抓取
        browser = None
        context = None
        playwright_instance = None
        try:
            from playwright.async_api import async_playwright
            playwright_instance = await async_playwright().start()
            browser = await playwright_instance.chromium.launch(headless=True)
            context = await browser.new_context()

            # 注入 cookie
            cookie_data, _ = await self._get_cookies()
            if cookie_data:
                # sameSite 只接受 Strict/Lax/None，过滤浏览器导出中的非法值
                # （如 "unspecified"/"no_restriction"），否则 add_cookies 会抛错。
                safe_cookies = []
                for c in cookie_data:
                    if not isinstance(c, dict):
                        continue
                    c = dict(c)  # 浅拷贝，避免污染调用方的原始数据
                    ss = c.get("sameSite")
                    if ss not in ("Strict", "Lax", "None"):
                        c["sameSite"] = "Lax"
                    safe_cookies.append(c)
                await context.add_cookies(safe_cookies)

            page = await context.new_page()
            # 导航到具体视频页以初始化环境（不要用首页，会因反爬超时）
            await page.goto(f"https://www.douyin.com/video/{post_id}", timeout=10000)

            # 浏览器中直接 fetch api 绕过 X-Bogus 计算
            api_url = f"https://www.douyin.com/aweme/v1/web/comment/list/?device_platform=webapp&aid=6383&aweme_id={post_id}&count={count}&cursor=0"
            eval_js = f"async () => {{ return await fetch('{api_url}').then(res => res.json()); }}"
            data = await page.evaluate(eval_js)
            
            raw_comments = data.get("comments", []) or []
            comments = []
            for item in raw_comments:
                user = item.get("user") or {}
                comments.append(Comment(
                    id=str(uuid.uuid4()),
                    task_id=task_id or str(uuid.uuid4()),
                    aweme_id=post_id,
                    cid=item.get("cid"),
                    user_id=user.get("uid"),
                    nickname=user.get("nickname"),
                    text=item.get("text"),
                    create_time=item.get("create_time", 0),
                    digg_count=item.get("digg_count", 0),
                    reply_comment_total=item.get("reply_comment_total", 0),
                    raw_data=item
                ))
            return comments
        except Exception as e:
            # 优雅降级：如果 Playwright 启动或者请求报错，退回到 curl_cffi
            try:
                from curl_cffi.requests import AsyncSession
                _, flattened_cookies = await self._get_cookies()
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36",
                    "Referer": "https://www.douyin.com/"
                }
                api_url = f"https://www.douyin.com/aweme/v1/web/comment/list/?device_platform=webapp&aid=6383&aweme_id={post_id}&count={count}&cursor=0"
                async with AsyncSession() as session:
                    resp = await session.get(api_url, headers=headers, cookies=flattened_cookies, impersonate="chrome110", timeout=10)
                if resp.status_code == 200:
                    data = resp.json()
                    raw_comments = data.get("comments", []) or []
                    comments = []
                    for item in raw_comments:
                        user = item.get("user") or {}
                        comments.append(Comment(
                            id=str(uuid.uuid4()),
                            task_id=task_id or str(uuid.uuid4()),
                            aweme_id=post_id,
                            cid=item.get("cid"),
                            user_id=user.get("uid"),
                            nickname=user.get("nickname"),
                            text=item.get("text"),
                            create_time=item.get("create_time", 0),
                            digg_count=item.get("digg_count", 0),
                            reply_comment_total=item.get("reply_comment_total", 0),
                            raw_data=item
                        ))
                    return comments
                else:
                    raise ValueError(f"HTTP status code: {resp.status_code}")
            except Exception as e2:
                # curl_cffi 兜底也失败。
                # prod 模式：抛出聚合异常，保留 Playwright 根因 e（而非被 e2 掩盖）。
                if self.test_mode != "mock":
                    raise RuntimeError(
                        f"Comment fetch failed via both channels - "
                        f"playwright_error={e}, curl_fallback_error={e2}"
                    ) from e
                # mock 模式：继续降级到本地 Mock 数据（见下方）。
            raw_comments = self._load_mock_data("comments_list.json")
            if not isinstance(raw_comments, list):
                raw_comments = []
            comments = []
            for item in raw_comments[:count]:
                user = item.get("user") or {}
                comments.append(Comment(
                    id=str(uuid.uuid4()),
                    task_id=task_id or str(uuid.uuid4()),
                    aweme_id=post_id,
                    cid=item.get("cid"),
                    user_id=user.get("uid"),
                    nickname=user.get("nickname"),
                    text=item.get("text"),
                    create_time=item.get("create_time", 0),
                    digg_count=item.get("digg_count", 0),
                    reply_comment_total=item.get("reply_comment_total", 0),
                    raw_data={"error": str(e), "fallback": True, **item}
                ))
            return comments
        finally:
            # 100% 彻底关闭释放 Playwright 资源
            if context:
                try:
                    await context.close()
                except Exception:
                    pass
            if browser:
                try:
                    await browser.close()
                except Exception:
                    pass
            if playwright_instance:
                try:
                    await playwright_instance.stop()
                except Exception:
                    pass

    def select_posts(self, posts: list[dict], config: dict) -> list[dict]:
        """
        排序与去重算法 (Top N + Recent N):
        Engagement Score 定义为：digg_count + comment_count + share_count (点赞 + 评论 + 分享)。
        对提取的所有 posts 分别进行如下两路排序过滤：
        1. 按照 Engagement Score 降序选择前 top_count 个。
        2. 按照 create_time 降序选择前 recent_count 个。
        合并两个子列表并基于 aweme_id 去重。
        """
        if config is None or not isinstance(config, dict):
            config = {}
        top_count = config.get("top_n", 5)
        recent_count = config.get("recent_n", 5)
        
        def get_score(post):
            stats = post.get("statistics") or {}
            digg = stats.get("digg_count", 0) or post.get("like_count", 0) or post.get("digg_count", 0) or 0
            comment = stats.get("comment_count", 0) or post.get("comment_count", 0) or 0
            share = stats.get("share_count", 0) or post.get("share_count", 0) or 0
            return digg + comment + share

        def get_create_time(post):
            return post.get("create_time", 0) or 0

        # 两路排序
        top_posts = sorted(posts, key=get_score, reverse=True)[:top_count]
        recent_posts = sorted(posts, key=get_create_time, reverse=True)[:recent_count]
        
        result = []
        seen = set()
        
        # 优先将 Top N 填入，确保最热门内容位于数组前列
        for post in top_posts:
            aid = post.get("aweme_id") or post.get("id")
            if aid:
                seen.add(aid)
                result.append(post)
                
        # 遍历 Recent N，将未出现在 Set 中的帖子追加到末尾
        for post in recent_posts:
            aid = post.get("aweme_id") or post.get("id")
            if aid and aid not in seen:
                seen.add(aid)
                result.append(post)
                
        return result

    async def download_video(self, video_url: str, video_id: str, output_path: str) -> bool:
        """
        下载备份视频逻辑
        """
        # 确保输出目录存在
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

        if self.test_mode == "mock":
            # 仅复制一个预存的测试 .mp4 模拟完成，或直接写入一个极小的模拟 mp4 数据以供测试
            # 检查是否有预存的测试 mp4
            test_mp4 = os.path.join(settings.BASE_DIR, "tests", "mock_data", "test.mp4")
            if os.path.exists(test_mp4):
                shutil.copy(test_mp4, output_path)
            else:
                # 写入 10 字节假的 mp4 数据
                with open(output_path, "wb") as f:
                    f.write(b"MOCK_MP4_DATA_12345")
            return True

        # 真实下载流程
        from curl_cffi.requests import AsyncSession
        
        last_exception = None

        # 1. 尝试主通道
        if video_url:
            try:
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36",
                    "Referer": "https://www.douyin.com/"
                }
                async with AsyncSession() as session:
                    resp = await session.get(video_url, headers=headers, impersonate="chrome110", timeout=15)
                if resp.status_code == 200:
                    with open(output_path, "wb") as f:
                        f.write(resp.content)
                    return True
                else:
                    raise RuntimeError(f"Main download channel returned status code {resp.status_code}")
            except Exception as e:
                last_exception = e

        # 2. 备用通道：Snssdk API 直链，重定向获取
        if video_id:
            try:
                snssdk_url = f"https://aweme.snssdk.com/aweme/v1/play/?video_id={video_id}&ratio=1080p&line=0"
                # 移动端 User-Agent
                headers = {
                    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1"
                }
                async with AsyncSession() as session:
                    resp = await session.get(snssdk_url, headers=headers, impersonate="chrome110", allow_redirects=True, timeout=15)
                if resp.status_code == 200:
                    with open(output_path, "wb") as f:
                        f.write(resp.content)
                    return True
                else:
                    raise RuntimeError(f"Backup download channel returned status code {resp.status_code}")
            except Exception as e:
                last_exception = e

        # 如果走到这说明下载失败了
        if self.test_mode != "mock":
            # 必须如实向外抛出下载网络或平台异常
            raise RuntimeError(f"Video download failed (url={video_url}, id={video_id})") from last_exception

        # 优雅降级：如果全部失败，并且在 mock 模式下，写入一个占位数据，防止系统挂掉
        try:
            with open(output_path, "wb") as f:
                f.write(b"MOCK_MP4_FALLBACK")
            return True
        except Exception:
            return False
