import pytest
import os
import json
from unittest.mock import patch, AsyncMock
from app.ai.registry import AIRegistry, ai_registry
from app.analyzers.base import BaseAnalyzer
from app.analyzers.visual_analyzer import VisualAnalyzer
from app.analyzers.comment_analyzer import CommentAnalyzer
from app.analyzers.profile_aggregator import ProfileAggregator
from app.models.blogger import BloggerProfile, CommenterProfile

class TestBaseAnalyzer:
    """测试 BaseAnalyzer 基础功能与安全的 JSON 解析器"""

    def test_init_default_registry(self):
        analyzer = BaseAnalyzer()
        assert analyzer.registry is ai_registry

    def test_init_custom_registry(self):
        custom_registry = AIRegistry()
        analyzer = BaseAnalyzer(registry=custom_registry)
        assert analyzer.registry is custom_registry

    def test_parse_json_safely_valid(self):
        analyzer = BaseAnalyzer()
        fallback = {"error": True}
        
        # 1. 干净的标准 JSON
        res = analyzer.parse_json_safely('{"a": 1, "b": "hello"}', fallback)
        assert res == {"a": 1, "b": "hello"}

    def test_parse_json_safely_markdown_json(self):
        analyzer = BaseAnalyzer()
        fallback = {"error": True}

        # 2. 带 ```json 块的格式
        res = analyzer.parse_json_safely('```json\n{"a": 1}\n```', fallback)
        assert res == {"a": 1}

        # 3. 带 ``` 块的格式
        res = analyzer.parse_json_safely('```\n{"a": 2}\n```', fallback)
        assert res == {"a": 2}

    def test_parse_json_safely_embedded(self):
        analyzer = BaseAnalyzer()
        fallback = {"error": True}

        # 4. 杂乱文本中嵌入了 JSON 字典
        text_with_prefix = "这里是分析结果：\n{\n  \"status\": \"ok\"\n}\n希望对你有用。"
        res = analyzer.parse_json_safely(text_with_prefix, fallback)
        assert res == {"status": "ok"}

        # 5. 杂乱文本中嵌入了 JSON 数组
        array_fallback = [{"id": 0}]
        text_with_array = "输出的数组如下：\n[\n  {\"id\": 1},\n  {\"id\": 2}\n]\n完毕。"
        res = analyzer.parse_json_safely(text_with_array, array_fallback)
        assert res == [{"id": 1}, {"id": 2}]

    def test_parse_json_safely_fallback(self):
        analyzer = BaseAnalyzer()
        fallback = {"error": True}

        # 6. 完全不合法的输入
        res = analyzer.parse_json_safely("这不是 JSON", fallback)
        assert res == fallback

        # 7. 空值
        res = analyzer.parse_json_safely("", fallback)
        assert res == fallback
        res = analyzer.parse_json_safely(None, fallback)
        assert res == fallback


class TestVisualAnalyzer:
    """测试 VisualAnalyzer 及其所有接口"""

    @pytest.fixture(autouse=True)
    def setup_mock_env(self):
        # 强制开启 mock 模式以便使用 MockProvider 的输出
        old_mode = os.environ.get("AROMOTION_TEST_MODE")
        os.environ["AROMOTION_TEST_MODE"] = "mock"
        yield
        if old_mode is not None:
            os.environ["AROMOTION_TEST_MODE"] = old_mode
        else:
            del os.environ["AROMOTION_TEST_MODE"]

    @pytest.mark.asyncio
    async def test_analyze_cover(self):
        analyzer = VisualAnalyzer()
        res = await analyzer.analyze_cover("dummy_cover.jpg")
        
        assert isinstance(res, dict)
        # 校验契约字段
        assert "穿搭单品" in res
        assert "搜索关键词" in res
        assert "scene" in res
        assert "场景和城市线索" in res
        assert "消费水平" in res
        assert "生活方式/审美倾向" in res
        
        # 校验同步逻辑 (scene 和 场景和城市线索 必须一致)
        assert res["scene"] == res["场景和城市线索"]
        assert isinstance(res["搜索关键词"], list)

    @pytest.mark.asyncio
    async def test_analyze_video_frame(self):
        analyzer = VisualAnalyzer()
        res = await analyzer.analyze_video_frame("dummy_frame.jpg")
        
        assert isinstance(res, dict)
        # 校验契约字段
        assert "wear" in res
        assert "wear_change" in res
        assert "consumption_level" in res

    @pytest.mark.asyncio
    async def test_analyze_grid(self):
        analyzer = VisualAnalyzer()
        
        # 测试有效人数组数为 3
        res = await analyzer.analyze_grid("dummy_grid.jpg", person_count=3)
        assert isinstance(res, list)
        assert len(res) == 3
        
        for i, item in enumerate(res):
            assert isinstance(item, dict)
            assert item["grid_index"] == i + 1
            assert "wear" in item
            assert "consumption_level" in item
            assert "style" in item


class TestCommentAnalyzer:
    """测试 CommentAnalyzer 及其所有接口"""

    @pytest.fixture(autouse=True)
    def setup_mock_env(self):
        old_mode = os.environ.get("AROMOTION_TEST_MODE")
        os.environ["AROMOTION_TEST_MODE"] = "mock"
        yield
        if old_mode is not None:
            os.environ["AROMOTION_TEST_MODE"] = old_mode
        else:
            del os.environ["AROMOTION_TEST_MODE"]

    @pytest.mark.asyncio
    async def test_analyze_comments(self):
        analyzer = CommentAnalyzer()
        comments = [
            {"text": "这件衣服太好看了，求链接！", "ip_label": "浙江"},
            {"text": "感觉一般般，不是很喜欢", "ip_label": "广东"},
            {"text": "尊嘟假嘟，太绝了吧", "ip_label": "四川"}
        ]
        
        res = await analyzer.analyze_comments(comments)
        
        assert isinstance(res, dict)
        # 校验顶级契约字段
        assert "keyword_stats" in res
        assert "sentiment_distribution" in res
        assert "purchase_intent" in res
        assert "dialect_features" in res
        assert "interaction_type" in res

        # 校验二级嵌套字段
        assert "positive" in res["sentiment_distribution"]
        assert "neutral" in res["sentiment_distribution"]
        assert "negative" in res["sentiment_distribution"]

        assert "level" in res["purchase_intent"]
        assert "signals" in res["purchase_intent"]

        assert "slang" in res["dialect_features"]
        assert "dialects" in res["dialect_features"]

        assert "question" in res["interaction_type"]
        assert "praise" in res["interaction_type"]
        assert "complaint" in res["interaction_type"]
        assert "other" in res["interaction_type"]

    @pytest.mark.asyncio
    async def test_analyze_comments_empty(self):
        analyzer = CommentAnalyzer()
        
        # 1. 传入空评论列表
        res = await analyzer.analyze_comments([])
        assert isinstance(res, dict)
        assert res["keyword_stats"] == {}
        
        # 2. 传入无 text 字段 of 评论列表
        res = await analyzer.analyze_comments([{"ip_label": "北京"}, {"text": "   "}])
        assert isinstance(res, dict)
        assert res["keyword_stats"] == {}


class TestProfileAggregator:
    """测试 ProfileAggregator 聚合流程、容错及兼容性"""

    @pytest.fixture(autouse=True)
    def setup_mock_env(self):
        old_mode = os.environ.get("AROMOTION_TEST_MODE")
        os.environ["AROMOTION_TEST_MODE"] = "mock"
        yield
        if old_mode is not None:
            os.environ["AROMOTION_TEST_MODE"] = old_mode
        else:
            del os.environ["AROMOTION_TEST_MODE"]

    @pytest.mark.asyncio
    async def test_aggregate_success_mocked(self):
        aggregator = ProfileAggregator()
        # 模拟真实 AI 返回的完整合法的 JSON
        mock_res_data = {
            "climate_consumption": {
                "climate_zone": {"湿热南方": 40.0, "干燥北方": 30.0, "四季分明": 30.0},
                "city_tier": {"一线/新一线": 50.0, "二线": 30.0, "三线及以下": 20.0},
                "culture_circle": {"日韩影响圈": 30.0, "内陆文化圈": 40.0, "港台风影响圈": 30.0},
                "concentration": "全国分散型",
                "summary": "气候-消费带总结"
            },
            "fragrance_consumption": {
                "price_tier": {"日常平价": 40.0, "轻奢入门": 30.0, "品质消费": 20.0, "高端消费": 10.0},
                "purchase_motivation": {"情绪需求": 40.0, "社交需求": 20.0, "身份需求": 10.0, "功能需求": 20.0, "收藏需求": 10.0},
                "decision_path": {"种草型": 50.0, "做功课型": 20.0, "冲动型": 20.0, "社交触发型": 10.0},
                "consumption_frequency": {"高频日常": 40.0, "场合驱动": 40.0, "低频尝鲜": 20.0},
                "summary": "香调消费总结"
            },
            "fashion_fragrance_map": {
                "fashion_style": {"甜美系": 40.0, "古典系": 30.0, "哥特系": 10.0, "国潮系": 10.0, "日常休闲": 10.0},
                "fashion_scene": {"拍照出片": 40.0, "日常通勤": 20.0, "聚会活动": 20.0, "约会社交": 20.0},
                "color_preference": {"粉色系": 40.0, "蓝紫系": 20.0, "黑白系": 20.0, "暖色系": 20.0},
                "fashion_completeness": {"精致": 50.0, "进阶": 20.0, "全套": 20.0, "基础": 10.0},
                "summary": "穿搭风格总结"
            },
            "lifestyle_scenario": {
                "core_interest": {"亚文化穿搭": 30.0, "日常自拍": 30.0, "二次元": 10.0, "旅行风景": 10.0, "其他": 20.0},
                "social_activity": {"圈层社交": 40.0, "高频社交": 20.0, "线上为主": 20.0, "独处型": 20.0},
                "aesthetic_personality": {"冒险型": 30.0, "收藏型": 30.0, "保守型": 20.0, "功能型": 20.0},
                "fragrance_timing": {"全天": 40.0, "白天为主": 20.0, "傍晚夜间": 20.0, "居家为主": 20.0},
                "content_consumption": {"种草转化型": 40.0, "深度参与型": 20.0, "情感共鸣型": 20.0, "路人围观型": 20.0},
                "summary": "生活方式总结"
            },
            "overall_summary": "总体总结",
            "full_report_markdown": "# 完整报告"
        }
        
        provider, model = aggregator._get_provider_for_slot("tag_aggregation")
        with patch.object(provider, "chat", new_callable=AsyncMock) as mock_chat:
            mock_chat.return_value = json.dumps(mock_res_data, ensure_ascii=False)
            
            blogger_profile = {
                "task_id": "test-task-123",
                "nickname": "TestBlogger",
                "platform": "douyin"
            }
            commenters = [
                {"province": "广东", "city": "广州"},
                {"province": "北京", "city": "北京"},
                {"province": "上海", "city": "上海"}
            ]
            
            report = await aggregator.aggregate(
                blogger_profile=blogger_profile,
                visual_analysis=[],
                comment_analysis={},
                commenter_profiles=commenters,
                fan_visual_analysis=[]
            )
            
            assert report.task_id == "test-task-123"
            assert report.id is not None
            assert report.overall_summary == "总体总结"
            assert report.full_report_markdown == "# 完整报告"
            assert report.climate_consumption["climate_zone"]["湿热南方"] == 40.0
            assert report.climate_consumption["city_tier"]["一线/新一线"] == 50.0

    @pytest.mark.asyncio
    async def test_aggregate_fallback_garbage(self):
        aggregator = ProfileAggregator()
        provider, model = aggregator._get_provider_for_slot("tag_aggregation")
        
        with patch.object(provider, "chat", new_callable=AsyncMock) as mock_chat:
            # 1. 模拟 AI 返回杂乱无章、不合法的非 JSON 字符串（且不包含 "收到您的反馈" 从而避开 mock 模式拦截）
            mock_chat.return_value = "这里是一些垃圾文本，根本不是 JSON 格式。"
            
            blogger_profile = {"task_id": "test-task-fallback"}
            report = await aggregator.aggregate(
                blogger_profile=blogger_profile,
                visual_analysis=[],
                comment_analysis={},
                commenter_profiles=[],
                fan_visual_analysis=[]
            )
            
            assert report.task_id == "test-task-fallback"
            assert report.overall_summary == "暂无画像报告总体摘要"
            assert report.climate_consumption["climate_zone"]["湿热南方"] == 0.0
            assert report.fragrance_consumption["price_tier"]["日常平价"] == 0.0

    @pytest.mark.asyncio
    async def test_aggregate_fallback_timeout(self):
        aggregator = ProfileAggregator()
        provider, model = aggregator._get_provider_for_slot("tag_aggregation")
        
        with patch.object(provider, "chat", new_callable=AsyncMock) as mock_chat:
            # 2. 模拟网络异常或超时抛出异常
            mock_chat.side_effect = Exception("Connection timeout")
            
            blogger_profile = {"task_id": "test-task-timeout"}
            report = await aggregator.aggregate(
                blogger_profile=blogger_profile,
                visual_analysis=[],
                comment_analysis={},
                commenter_profiles=[],
                fan_visual_analysis=[]
            )
            
            assert report.task_id == "test-task-timeout"
            assert report.overall_summary == "暂无画像报告总体摘要"
            assert report.climate_consumption["summary"] == "暂无气候-消费带分析摘要"

    @pytest.mark.asyncio
    async def test_aggregate_compatibility(self):
        aggregator = ProfileAggregator()
        
        # 模拟 SQLAlchemy model 实例
        # 注意：platform 字段位于 AnalysisTask，而非 BloggerProfile
        blogger_model = BloggerProfile(
            task_id="model-task-111",
            nickname="ModelBlogger",
            gender="女",
            age="25",
            province="广东省",
            city="广州市",
            follower_count=100000,
            platform_uid="123456",
            raw_data={}
        )
        
        commenter_models = [
            CommenterProfile(
                task_id="model-task-111",
                platform_uid="c1",
                nickname="Fan1",
                province="广东省",
                city="深圳市",
                raw_data={}
            ),
            CommenterProfile(
                task_id="model-task-111",
                platform_uid="c2",
                nickname="Fan2",
                province="北京市",
                city="北京市",
                raw_data={}
            )
        ]
        
        # 兼容性测试，在 mock 模式下直接调用，验证提取逻辑
        report = await aggregator.aggregate(
            blogger_profile=blogger_model,
            visual_analysis=[],
            comment_analysis={},
            commenter_profiles=commenter_models,
            fan_visual_analysis=[]
        )
        
        assert report.task_id == "model-task-111"
        assert report.overall_summary is not None
        assert report.climate_consumption["climate_zone"]["湿热南方"] is not None

