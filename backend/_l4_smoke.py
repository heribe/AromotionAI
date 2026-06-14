"""L4 第一步：单独测抖音采集器（磁盘 cookie fallback）。
验证 cookie 有效 + 抖音 web API 通不通，不走 service/pipeline。

用法: python _l4_smoke.py <博主主页URL或sec_user_id>
"""
import app.config  # 触发 load_dotenv
import asyncio
import sys

# Windows 终端默认 GBK，emoji/特殊字符会触发 UnicodeEncodeError；统一 utf-8 + replace
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# 注意导入顺序：必须先触发 app.services 按正常顺序初始化（analysis_service 先于
# collector 被加载），否则直接 import collector 会陷入循环导入——
# collector → cookie_service → services/__init__ → analysis_service → collector。
# 正常服务启动走 main.py→router→analysis API→analysis_service 不触发，但单独
# import collector 会炸。这反映 collector↔services 存在循环依赖（既有代码，脆弱点）。
import app.services.analysis_service  # noqa: F401
from app.platforms.douyin.collector import DouyinCollector


async def main():
    if len(sys.argv) < 2:
        print("请提供博主主页 URL: python _l4_smoke.py <url>")
        sys.exit(1)
    blogger_url = sys.argv[1]

    # db=None → 走磁盘 cookie fallback (backend/data/cookies/douyin.json)
    # test_mode="prod" → 真实请求，不走 mock
    collector = DouyinCollector(db=None, test_mode="prod")

    print("=== 1. get_blogger_profile（验证 cookie 鉴权 + user/profile API）===")
    uid = None
    try:
        profile = await collector.get_blogger_profile(blogger_url, task_id="l4-smoke")
        print("  nickname      :", profile.nickname)
        print("  platform_uid  :", profile.platform_uid)
        print("  follower_count:", profile.follower_count)
        print("  city/province :", profile.city, "/", profile.province)
        raw = profile.raw_data or {}
        if isinstance(raw, dict) and "user" in raw:
            # 真实响应结构
            print("  raw_status    : 真实数据（含 user 字段）✅")
        else:
            print("  raw_status    : 可能降级到 mock（raw_data 无 user 字段）⚠️ raw keys:", list(raw.keys())[:5] if isinstance(raw, dict) else type(raw))
        uid = profile.platform_uid
        print("  → profile 采集成功")
    except Exception as e:
        print("  ✗ profile 失败:", type(e).__name__, str(e)[:400])
        return

    print()
    print("=== 2. get_blogger_posts（模拟 AnalysisService 修复后的提取逻辑）===")
    # 复刻 analysis_service.py 的修复：从 profile 响应 raw_data["user"]["sec_uid"] 提取
    _raw_user = (profile.raw_data or {}).get("user") or {}
    sec_uid = _raw_user.get("sec_uid") or profile.platform_uid
    print(f"  platform_uid (数字)  = {profile.platform_uid}")
    print(f"  sec_uid (从raw提取)  = {sec_uid[:40]}...")
    print(f"  → 传给 get_blogger_posts 的是 sec_uid（非数字 uid）: {sec_uid != str(profile.platform_uid)}")
    try:
        posts = await collector.get_blogger_posts(sec_uid, count=3, task_id="l4-smoke")
        print(f"  获取 {len(posts)} 条帖子")
        for p in posts[:3]:
            print(f"   - aweme_id={p.aweme_id} like={p.like_count} comment={p.comment_count} share={p.share_count}")
        if posts:
            print("  → posts 采集成功 ✅")
        else:
            print("  ⚠️ posts 为空（接口返回空 / 被风控 / 该博主无作品）")
    except Exception as e:
        print("  ✗ posts 失败:", type(e).__name__, str(e)[:400])


if __name__ == "__main__":
    asyncio.run(main())
