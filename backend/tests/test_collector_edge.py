"""
Edge-case tests for DouyinCollector methods that the main test_douyin_collector.py
does not fully cover.

Focus areas:
  - select_posts deduplication boundaries (no overlap / full overlap / custom N)
  - select_posts with aweme_id absent (falls back to `id` key)
  - download_video backup-only path (video_url empty, video_id present)
  - download_video prod success via backup channel when main URL is empty

R2 Three-Question Self-Check:
1. Contract Closure: Each documented contract branch of select_posts and
   download_video is exercised with crafted inputs.
2. Symmetry: No persistent resources created; tmp_path isolates all disk I/O.
3. External Timing: Async methods use deterministic mocks (no real network).
"""

import os

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.platforms.douyin.collector import DouyinCollector


def _post(aid, create_time, digg=0, comment=0, share=0):
    """Helper: build a raw post dict shaped like the real API payload."""
    return {
        "aweme_id": aid,
        "create_time": create_time,
        "statistics": {
            "digg_count": digg,
            "comment_count": comment,
            "share_count": share,
        },
    }


def test_select_posts_top_and_recent_disjoint():
    """When Top N and Recent N share no members, the result is their union
    with Top entries first and Recent entries appended after."""
    collector = DouyinCollector()
    # p1 hottest, p2 second hottest; but p3, p4 are newest in time.
    posts = [
        _post("p1", 100, digg=100),
        _post("p2", 200, digg=50),
        _post("p3", 500, digg=1),
        _post("p4", 600, digg=1),
    ]
    selected = collector.select_posts(posts, {"top_n": 2, "recent_n": 2})

    assert [p["aweme_id"] for p in selected] == ["p1", "p2", "p4", "p3"]


def test_select_posts_top_and_recent_fully_overlap():
    """When the same posts are both top and recent (small input set),
    dedup must collapse them so no entry appears twice."""
    collector = DouyinCollector()
    posts = [
        _post("only", 999, digg=999),
    ]
    selected = collector.select_posts(posts, {"top_n": 5, "recent_n": 5})

    assert len(selected) == 1
    assert selected[0]["aweme_id"] == "only"


def test_select_posts_uses_id_when_aweme_id_missing():
    """Posts lacking aweme_id fall back to the `id` key for dedup tracking."""
    collector = DouyinCollector()
    posts = [
        {"id": "fallback1", "create_time": 100, "statistics": {"digg_count": 10}},
        {"id": "fallback2", "create_time": 200, "statistics": {"digg_count": 5}},
    ]
    selected = collector.select_posts(posts, {"top_n": 2, "recent_n": 2})

    assert len(selected) == 2
    ids = {p["id"] for p in selected}
    assert ids == {"fallback1", "fallback2"}


def test_select_posts_empty_input():
    """An empty post list yields an empty result, not an error."""
    collector = DouyinCollector()
    assert collector.select_posts([], {"top_n": 3, "recent_n": 3}) == []


def test_select_posts_default_counts_when_config_omits_keys():
    """Missing top_n / recent_n fall back to the default of 5 each.

    Craft data so Top 5 (by score) and Recent 5 (by time) are disjoint:
    - p0..p4: high digg but OLD create_time  -> land in Top, not Recent
    - p5..p9: low digg but NEW create_time   -> land in Recent, not Top
    With defaults top_n=5, recent_n=5, the union has 10 distinct entries.
    """
    collector = DouyinCollector()
    posts = [_post(f"p{i}", create_time=i, digg=100 - i) for i in range(10)]
    # Wait: that makes high-digg also new. Invert create_time so old posts are hot.
    posts = [
        _post(f"hot{i}", create_time=i, digg=100) for i in range(5)        # old, hot
    ] + [
        _post(f"new{i}", create_time=1000 + i, digg=1) for i in range(5)   # new, cold
    ]
    selected = collector.select_posts(posts, {})

    assert len(selected) == 10
    hot_ids = {p["aweme_id"] for p in selected[:5]}
    new_ids = {p["aweme_id"] for p in selected[5:]}
    assert hot_ids == {f"hot{i}" for i in range(5)}
    assert new_ids == {f"new{i}" for i in range(5)}


@pytest.mark.asyncio
async def test_download_video_backup_only_channel(tmp_path):
    """When video_url is empty but video_id is given, only the backup
    (snssdk) channel is attempted. A 200 there must succeed."""
    collector_prod = DouyinCollector(test_mode="prod")
    out_path = str(tmp_path / "backup_only.mp4")

    async def get_side_effect(url, *args, **kwargs):
        # Backup channel URL contains snssdk.com
        assert "snssdk.com" in url
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.content = b"BACKUP_VIDEO_CONTENT"
        return mock_resp

    mock_sess = MagicMock()
    mock_sess.__aenter__.return_value = mock_sess
    mock_sess.get = AsyncMock(side_effect=get_side_effect)

    # video_url is empty -> main channel skipped entirely.
    with patch("curl_cffi.requests.AsyncSession", return_value=mock_sess):
        res = await collector_prod.download_video("", "vid_001", out_path)
        assert res is True
        with open(out_path, "rb") as f:
            assert f.read() == b"BACKUP_VIDEO_CONTENT"


@pytest.mark.asyncio
async def test_download_video_no_url_no_id_raises_in_prod(tmp_path):
    """With both video_url and video_id empty in prod mode, there is nothing
    to try; the final RuntimeError must be raised."""
    collector_prod = DouyinCollector(test_mode="prod")
    out_path = str(tmp_path / "nothing.mp4")

    with patch("curl_cffi.requests.AsyncSession") as mock_session_cls:
        with pytest.raises(RuntimeError) as exc_info:
            await collector_prod.download_video("", "", out_path)
        assert "Video download failed" in str(exc_info.value)
        # Neither channel should have been entered.
        assert mock_session_cls.call_count == 0


@pytest.mark.asyncio
async def test_collect_comments_samesite_normalization():
    """Cookies exported by browsers often carry sameSite values that Playwright
    rejects (e.g. 'unspecified', 'no_restriction', missing). collect_comments
    must normalize them to an accepted value before add_cookies, otherwise the
    Playwright channel crashes on cookie injection."""
    collector_prod = DouyinCollector(test_mode="prod")

    captured = {}

    class FakeContext:
        async def add_cookies(self, cookies):
            captured["cookies"] = cookies

        async def new_page(self):
            page = AsyncMock()
            page.evaluate = AsyncMock(return_value={"comments": []})
            return page

        async def close(self):
            pass

    class FakeBrowser:
        async def new_context(self):
            return FakeContext()

        async def close(self):
            pass

    class FakePlaywright:
        chromium = MagicMock()

        async def stop(self):
            pass

    fake_pw = FakePlaywright()
    fake_pw.chromium.launch = AsyncMock(return_value=FakeBrowser())
    fake_pw.start = AsyncMock(return_value=fake_pw)

    # _get_cookies 返回含非法 sameSite 值的 cookie 列表
    bad_cookies = [
        {"name": "a", "value": "1", "sameSite": "unspecified"},
        {"name": "b", "value": "2", "sameSite": "no_restriction"},
        {"name": "c", "value": "3"},  # 缺 sameSite
        {"name": "d", "value": "4", "sameSite": "Strict"},  # 合法，应保留
        "not_a_dict",  # 非法元素，应被跳过
    ]

    async def fake_get_cookies():
        return bad_cookies, {}

    with patch("playwright.async_api.async_playwright", return_value=fake_pw):
        with patch.object(collector_prod, "_get_cookies", side_effect=fake_get_cookies):
            comments = await collector_prod.collect_comments("post_xyz", count=1)

    assert comments == []
    injected = captured["cookies"]
    # 非法 dict 元素 "not_a_dict" 被过滤
    assert len(injected) == 4
    samesites = {c["sameSite"] for c in injected}
    # 所有 sameSite 都必须是 Playwright 接受的值
    assert samesites.issubset({"Strict", "Lax", "None"})
    # "Strict" 保留原值
    strict = [c for c in injected if c["name"] == "d"][0]
    assert strict["sameSite"] == "Strict"
    # 其余非法值归一化为 "Lax"
    others = {c["name"]: c["sameSite"] for c in injected if c["name"] != "d"}
    assert all(v == "Lax" for v in others.values())
