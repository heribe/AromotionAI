import pytest
import os
import json
from app.ai.registry import AIRegistry, ai_registry
from app.analyzers.base import BaseAnalyzer
from app.analyzers.visual_analyzer import VisualAnalyzer
from app.analyzers.comment_analyzer import CommentAnalyzer

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
        
        # 2. 传入无 text 字段的评论列表
        res = await analyzer.analyze_comments([{"ip_label": "北京"}, {"text": "   "}])
        assert isinstance(res, dict)
        assert res["keyword_stats"] == {}
