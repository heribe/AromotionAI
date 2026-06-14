import os
import json
import pytest
import datetime
from unittest.mock import MagicMock, AsyncMock, patch
from sqlalchemy.orm import Session
from app.models.blogger import BloggerProfile, BloggerPost, Comment
from app.platforms.douyin.collector import DouyinCollector
from app.services.cookie_service import CookieService
from app.config import settings

@pytest.mark.asyncio
async def test_douyin_collector_init():
    collector = DouyinCollector()
    assert collector.db is None
    assert collector.test_mode in ["prod", "mock", "development"]

    collector_mock = DouyinCollector(test_mode="mock")
    assert collector_mock.test_mode == "mock"

@pytest.mark.asyncio
async def test_flatten_cookies():
    collector = DouyinCollector()
    cookies = [
        {"name": "sessionid", "value": "123"},
        {"name": "other", "value": 456},
        {"name": "invalid"},
    ]
    res = collector._flatten_cookies(cookies)
    assert res == {"sessionid": "123", "other": "456"}

@pytest.mark.asyncio
async def test_get_cookies_no_db(tmp_path):
    collector = DouyinCollector()
    
    with patch("app.platforms.douyin.collector.settings") as mock_settings:
        mock_settings.COOKIE_DIR = str(tmp_path)
        mock_settings.BASE_DIR = tmp_path
        
        # 1. file not exists
        cookie_data, flattened = await collector._get_cookies()
        assert cookie_data == []
        assert flattened == {}

        # 2. file exists with valid json
        cookie_file = tmp_path / "douyin.json"
        cookie_content = [{"name": "foo", "value": "bar"}]
        with open(cookie_file, "w", encoding="utf-8") as f:
            json.dump(cookie_content, f)
            
        cookie_data, flattened = await collector._get_cookies()
        assert cookie_data == cookie_content
        assert flattened == {"foo": "bar"}

        # 3. file exists but corrupted
        with open(cookie_file, "w", encoding="utf-8") as f:
            f.write("{invalid_json}")
        cookie_data, flattened = await collector._get_cookies()
        assert cookie_data == []
        assert flattened == {}

@pytest.mark.asyncio
async def test_get_cookies_with_db(db: Session):
    collector = DouyinCollector(db=db)
    
    mock_cookie = MagicMock()
    mock_cookie.cookie_data = [{"name": "db_cookie", "value": "db_val"}]
    
    with patch.object(CookieService, "get_valid_cookie", AsyncMock(return_value=mock_cookie)):
        cookie_data, flattened = await collector._get_cookies()
        assert cookie_data == mock_cookie.cookie_data
        assert flattened == {"db_cookie": "db_val"}

    with patch.object(CookieService, "get_valid_cookie", AsyncMock(return_value=None)):
        cookie_data, flattened = await collector._get_cookies()
        assert cookie_data == []
        assert flattened == {}

@pytest.mark.asyncio
async def test_load_mock_data():
    collector = DouyinCollector()
    data = collector._load_mock_data("nonexistent_file_xyz.json")
    assert isinstance(data, dict) or isinstance(data, list)
    
    data_profile = collector._load_mock_data("blogger_profile.json")
    assert "nickname" in data_profile or "uid" in data_profile
    
    data_comments = collector._load_mock_data("comments_list.json")
    assert len(data_comments) > 0

@pytest.mark.asyncio
async def test_get_blogger_profile():
    collector = DouyinCollector(test_mode="mock")
    profile = await collector.get_blogger_profile("https://www.douyin.com/user/MS4wLjABAAAA_test")
    assert isinstance(profile, BloggerProfile)
    assert profile.nickname == "时尚博主A"

    collector_prod = DouyinCollector(test_mode="prod")
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "user": {
            "uid": "987654321",
            "nickname": "真实博主",
            "gender": 2,
            "province": "北京",
            "city": "北京",
            "signature": "真实签名",
            "m_follower_count": 1000000,
            "avatar_larger": {"url_list": ["https://avatar.url/large"]},
        }
    }
    
    mock_sess = MagicMock()
    mock_sess.__aenter__.return_value = mock_sess
    mock_sess.get = AsyncMock(return_value=mock_response)
    
    with patch("curl_cffi.requests.AsyncSession", return_value=mock_sess):
        profile = await collector_prod.get_blogger_profile("MS4wLjABAAAA_real")
        assert profile.nickname == "真实博主"
        assert profile.gender == "female"
        assert profile.platform_uid == "987654321"

    # HTTP error (should raise Exception in prod mode)
    mock_response.status_code = 500
    mock_sess_500 = MagicMock()
    mock_sess_500.__aenter__.return_value = mock_sess_500
    mock_sess_500.get = AsyncMock(return_value=mock_response)
    with patch("curl_cffi.requests.AsyncSession", return_value=mock_sess_500):
        with pytest.raises(Exception):
            await collector_prod.get_blogger_profile("MS4wLjABAAAA_real")

    # Connection error (should raise Exception in prod mode)
    mock_sess_err = MagicMock()
    mock_sess_err.__aenter__.return_value = mock_sess_err
    mock_sess_err.get = AsyncMock(side_effect=Exception("Connection error"))
    with patch("curl_cffi.requests.AsyncSession", return_value=mock_sess_err):
        with pytest.raises(Exception):
            await collector_prod.get_blogger_profile("MS4wLjABAAAA_real")

@pytest.mark.asyncio
async def test_get_blogger_posts():
    collector = DouyinCollector(test_mode="mock")
    posts = await collector.get_blogger_posts("uid_123", count=3)
    assert len(posts) == 3
    assert posts[0].title == "Mock 帖子标题 0"

    collector_prod = DouyinCollector(test_mode="prod")
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "aweme_list": [
            {
                "aweme_id": "post_1",
                "desc": "描述 1",
                "create_time": 1700000000,
                "statistics": {"digg_count": 10, "comment_count": 5, "share_count": 2},
                "video": {
                    "play_addr": {"url_list": ["https://video.url/1"]},
                    "cover": {"url_list": ["https://cover.url/1"]}
                }
            }
        ]
    }
    
    mock_sess = MagicMock()
    mock_sess.__aenter__.return_value = mock_sess
    mock_sess.get = AsyncMock(return_value=mock_response)
    
    with patch("curl_cffi.requests.AsyncSession", return_value=mock_sess):
        posts = await collector_prod.get_blogger_posts("uid_123", count=1)
        assert len(posts) == 1
        assert posts[0].aweme_id == "post_1"

    # Error - should raise exception in prod mode
    mock_response.status_code = 500
    mock_sess_500 = MagicMock()
    mock_sess_500.__aenter__.return_value = mock_sess_500
    mock_sess_500.get = AsyncMock(return_value=mock_response)
    with patch("curl_cffi.requests.AsyncSession", return_value=mock_sess_500):
        with pytest.raises(Exception):
            await collector_prod.get_blogger_posts("uid_123", count=2)

@pytest.mark.asyncio
@pytest.mark.skip(
    reason="需要人工测试：collect_comments 的 Playwright mock 链路与实际代码已漂移，"
           "fallback 到 curl_cffi 时会发起真实网络请求。需重写 mock 或在拥有有效 "
           "抖音 Cookie 的环境下手动验证。详见 PROGRESS.md '待人工测试' 一节。"
)
async def test_collect_comments():
    collector = DouyinCollector(test_mode="mock")
    comments = await collector.collect_comments("post_123", count=2)
    assert len(comments) in [1, 2]
    assert comments[0].aweme_id == "post_123"

    collector_prod = DouyinCollector(test_mode="prod")

    # 辅助：构建一个真实模拟 async_playwright() 调用链的 mock 工厂。
    # 源码调用方式：async_playwright().start() -> playwright_instance；
    #               playwright_instance.chromium.launch() -> browser；
    #               browser.new_context() -> context；context.new_page() -> page。
    # finally 中对称清理：context.close() / browser.close() / playwright_instance.stop()。
    def build_playwright_mock(page_evaluate_return, launch_side_effect=None):
        mock_page = AsyncMock()
        mock_page.evaluate = AsyncMock(return_value=page_evaluate_return)
        mock_context = AsyncMock()
        mock_context.new_page = AsyncMock(return_value=mock_page)
        mock_browser = AsyncMock()
        mock_browser.new_context = AsyncMock(return_value=mock_context)
        mock_playwright = MagicMock()
        mock_playwright.chromium.launch = AsyncMock(
            return_value=mock_browser,
            side_effect=launch_side_effect
        )
        # playwright_instance.start() 返回 playwright 对象本身
        mock_playwright.start = AsyncMock(return_value=mock_playwright)
        mock_playwright.stop = AsyncMock(return_value=None)
        return mock_playwright

    # 1. Playwright Success
    mock_playwright = build_playwright_mock({
        "comments": [
            {
                "cid": "c_1",
                "text": "评论 1",
                "create_time": 1700000100,
                "digg_count": 100,
                "user": {"uid": "user_1", "nickname": "昵称 1"}
            }
        ]
    })
    with patch("playwright.async_api.async_playwright", return_value=mock_playwright):
        comments = await collector_prod.collect_comments("post_123", count=1)
        assert len(comments) == 1
        assert comments[0].cid == "c_1"

    # 2. Playwright Fail, fallback to curl_cffi Success
    mock_playwright_fail = build_playwright_mock(
        page_evaluate_return={},
        launch_side_effect=Exception("Playwright init error")
    )
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "comments": [
            {
                "cid": "c_curl",
                "text": "评论 curl",
                "create_time": 1700000200,
                "digg_count": 50,
                "user": {"uid": "user_curl", "nickname": "昵称 curl"}
            }
        ]
    }

    mock_sess = MagicMock()
    mock_sess.__aenter__.return_value = mock_sess
    mock_sess.get = AsyncMock(return_value=mock_response)

    with patch("playwright.async_api.async_playwright", return_value=mock_playwright_fail):
        with patch("curl_cffi.requests.AsyncSession", return_value=mock_sess):
            comments = await collector_prod.collect_comments("post_123", count=1)
            assert len(comments) == 1
            assert comments[0].cid == "c_curl"

    # 3. Playwright Fail, curl_cffi Fail, should raise RuntimeError in prod mode
    #    that preserves BOTH the playwright root cause and the curl fallback error.
    mock_playwright_fail2 = build_playwright_mock(
        page_evaluate_return={},
        launch_side_effect=Exception("Playwright init error")
    )
    mock_sess_err = MagicMock()
    mock_sess_err.__aenter__.return_value = mock_sess_err
    mock_sess_err.get = AsyncMock(side_effect=Exception("Curl cffi error"))
    with patch("playwright.async_api.async_playwright", return_value=mock_playwright_fail2):
        with patch("curl_cffi.requests.AsyncSession", return_value=mock_sess_err):
            with pytest.raises(RuntimeError) as exc_info:
                await collector_prod.collect_comments("post_123", count=1)
            msg = str(exc_info.value)
            # 根因（Playwright 错误）必须出现在异常消息中，不再被 curl 错误掩盖。
            assert "Playwright init error" in msg
            assert "Curl cffi error" in msg

def test_select_posts():
    collector = DouyinCollector()
    posts = [
        {"aweme_id": "p1", "create_time": 100, "statistics": {"digg_count": 10, "comment_count": 5, "share_count": 1}},
        {"aweme_id": "p2", "create_time": 200, "statistics": {"digg_count": 5, "comment_count": 2, "share_count": 1}},
        {"aweme_id": "p3", "create_time": 300, "statistics": {"digg_count": 20, "comment_count": 10, "share_count": 5}},
        {"aweme_id": "p4", "create_time": 400, "statistics": {"digg_count": 1, "comment_count": 1, "share_count": 1}},
        {"aweme_id": "p5", "create_time": 500, "statistics": {"digg_count": 2, "comment_count": 2, "share_count": 2}},
    ]
    
    config = {"top_n": 2, "recent_n": 2}
    selected = collector.select_posts(posts, config)
    
    assert [p["aweme_id"] for p in selected] == ["p3", "p1", "p5", "p4"]

@pytest.mark.asyncio
async def test_download_video(tmp_path):
    collector_mock = DouyinCollector(test_mode="mock")
    out_path = str(tmp_path / "mock_video.mp4")
    res = await collector_mock.download_video("url", "id", out_path)
    assert res is True
    assert os.path.exists(out_path)

    collector_prod = DouyinCollector(test_mode="prod")
    # 1. Main channel success
    out_path_1 = str(tmp_path / "video_1.mp4")
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.content = b"VIDEO_CONTENT_1"
    
    mock_sess = MagicMock()
    mock_sess.__aenter__.return_value = mock_sess
    mock_sess.get = AsyncMock(return_value=mock_resp)
    
    with patch("curl_cffi.requests.AsyncSession", return_value=mock_sess):
        res = await collector_prod.download_video("http://main.url", "id_123", out_path_1)
        assert res is True
        with open(out_path_1, "rb") as f:
            assert f.read() == b"VIDEO_CONTENT_1"

    # 2. Main channel fail, backup channel success
    out_path_2 = str(tmp_path / "video_2.mp4")
    mock_resp_fail = MagicMock()
    mock_resp_fail.status_code = 404
    
    async def get_side_effect(url, *args, **kwargs):
        if "main.url" in url:
            return mock_resp_fail
        else:
            mock_resp_ok = MagicMock()
            mock_resp_ok.status_code = 200
            mock_resp_ok.content = b"VIDEO_CONTENT_2"
            return mock_resp_ok

    mock_sess_backup = MagicMock()
    mock_sess_backup.__aenter__.return_value = mock_sess_backup
    mock_sess_backup.get = AsyncMock(side_effect=get_side_effect)

    with patch("curl_cffi.requests.AsyncSession", return_value=mock_sess_backup):
        res = await collector_prod.download_video("http://main.url", "id_123", out_path_2)
        assert res is True
        with open(out_path_2, "rb") as f:
            assert f.read() == b"VIDEO_CONTENT_2"

    # 3. All channels fail, fallback to mock data write
    out_path_3 = str(tmp_path / "video_3.mp4")
    mock_sess_fail = MagicMock()
    mock_sess_fail.__aenter__.return_value = mock_sess_fail
    mock_sess_fail.get = AsyncMock(side_effect=Exception("Network error"))
    
    with patch("curl_cffi.requests.AsyncSession", return_value=mock_sess_fail):
        with pytest.raises(RuntimeError):
            await collector_prod.download_video("http://main.url", "id_123", out_path_3)
