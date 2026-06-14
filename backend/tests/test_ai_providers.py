import pytest
import os
import json
import re
import threading
from app.ai.base import AIProvider
from app.ai.provider_openai import OpenAIProvider
from app.ai.provider_glm import GLMProvider
from app.ai.provider_deepseek import DeepSeekProvider
from app.ai.registry import AIRegistry


class TestAIProviderContract:
    """1. 基类与子类契约验证"""

    def test_provider_inheritance(self):
        assert issubclass(OpenAIProvider, AIProvider)
        assert issubclass(GLMProvider, AIProvider)
        assert issubclass(DeepSeekProvider, AIProvider)

    def test_provider_properties(self):
        openai_p = OpenAIProvider()
        glm_p = GLMProvider()
        deepseek_p = DeepSeekProvider()

        # 检查属性和方法定义
        for p in [openai_p, glm_p, deepseek_p]:
            assert hasattr(p, "chat")
            assert hasattr(p, "vision")
            assert hasattr(p, "name")
            assert hasattr(p, "supports_vision")
            assert isinstance(p.name, str)
            assert isinstance(p.supports_vision, bool)

        assert openai_p.name == "openai"
        assert openai_p.supports_vision is True

        assert glm_p.name == "glm"
        assert glm_p.supports_vision is True

        assert deepseek_p.name == "deepseek"
        assert deepseek_p.supports_vision is False

    @pytest.mark.asyncio
    async def test_deepseek_vision_not_implemented(self):
        deepseek_p = DeepSeekProvider()
        with pytest.raises(NotImplementedError) as exc_info:
            await deepseek_p.vision(image_paths=["dummy.jpg"], prompt="Analyze this")
        assert "DeepSeek API does not support vision capability." in str(exc_info.value)


class TestAIRegistrySlotBinding:
    """2. 槽位绑定逻辑与配置安全验证"""

    def test_default_slot_bindings(self):
        registry = AIRegistry()
        
        # 验证默认绑定的槽位映射。
        # 默认 model 由环境变量 GLM_MODEL / GLM_VISION_MODEL 控制，未配置时回退 glm-5.2。
        expected_bindings = {
            "visual_analysis": ("glm", "glm-5.2"),
            "comment_analysis": ("glm", "glm-5.2"),
            "tag_aggregation": ("glm", "glm-5.2"),
            "fragrance_reasoning": ("glm", "glm-5.2"),
            "fragrance_chat": ("glm", "glm-5.2"),
            "analysis_task": ("glm", "glm-5.2"),
        }

        for slot_id, (expected_prov, expected_model) in expected_bindings.items():
            provider, model = registry.get_provider_for_slot(slot_id)
            assert provider.name == expected_prov
            assert model == expected_model

    def test_incompatible_vision_binding_raises_value_error(self):
        registry = AIRegistry()
        # 校验不兼容的视觉插槽绑定（将不支持视觉的 deepseek 绑定到 visual_analysis）
        with pytest.raises(ValueError) as exc_info:
            registry.bind_slot("visual_analysis", "deepseek", "deepseek-chat")
        assert "does not support vision capability for slot 'visual_analysis'" in str(exc_info.value)

        # 校验正常绑定非视觉槽位
        registry.bind_slot("comment_analysis", "deepseek", "deepseek-chat")
        provider, model = registry.get_provider_for_slot("comment_analysis")
        assert provider.name == "deepseek"
        assert model == "deepseek-chat"

    def test_concurrent_binding_thread_safety(self):
        """验证 AIRegistry 支持高并发的槽位绑定与动态配置更新，在并发下是线程安全的"""
        registry = AIRegistry()
        
        # 定义一个在线程中运行的函数，并发地进行绑定和读取操作
        def worker(thread_idx):
            # 交替绑定不同的 provider
            for i in range(100):
                prov_name = "openai" if (thread_idx + i) % 2 == 0 else "glm"
                model_name = "gpt-4o" if prov_name == "openai" else "glm-4"
                
                # 绑定到 tag_aggregation (非视觉槽位)
                registry.bind_slot("tag_aggregation", prov_name, model_name)
                
                # 读取并验证绑定是否正确 (必须成功获取，模型名字匹配对应的 provider)
                provider, bound_model = registry.get_provider_for_slot("tag_aggregation")
                assert provider.name in ["openai", "glm"]
                if provider.name == "openai":
                    assert bound_model == "gpt-4o"
                else:
                    assert bound_model == "glm-4"

        # 启动 10 个线程并发执行
        threads = []
        for idx in range(10):
            t = threading.Thread(target=worker, args=(idx,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # 确保并发后状态依然一致
        provider, bound_model = registry.get_provider_for_slot("tag_aggregation")
        assert provider.name in ["openai", "glm"]


class TestMockModeVerification:
    """3. Mock 模式校验"""

    @pytest.fixture(autouse=True)
    def setup_mock_env(self):
        # 备份并设置环境变量
        old_mode = os.environ.get("AROMOTION_TEST_MODE")
        os.environ["AROMOTION_TEST_MODE"] = "mock"
        yield
        if old_mode is not None:
            os.environ["AROMOTION_TEST_MODE"] = old_mode
        else:
            del os.environ["AROMOTION_TEST_MODE"]

    @pytest.mark.asyncio
    async def test_mock_chat_without_api_keys(self):
        # 创建空密钥的 provider，验证在 mock 模式下不用真实密钥也正常工作
        openai_p = OpenAIProvider(api_key=None)
        glm_p = GLMProvider(api_key=None)
        deepseek_p = DeepSeekProvider(api_key=None)

        assert openai_p.is_mock_mode() is True
        assert glm_p.is_mock_mode() is True
        assert deepseek_p.is_mock_mode() is True

        messages = [{"role": "user", "content": "hello"}]
        
        # 验证 chat 调用能正常返回默认的 Mock 数据而非发起 HTTP 请求
        res_openai = await openai_p.chat(messages)
        res_glm = await glm_p.chat(messages)
        res_deepseek = await deepseek_p.chat(messages)

        for res in [res_openai, res_glm, res_deepseek]:
            assert isinstance(res, str)
            assert "收到您的反馈" in res

    @pytest.mark.asyncio
    async def test_mock_chat_keywords_tuning(self):
        openai_p = OpenAIProvider(api_key=None)

        # 1. 验证 woody / 沉香 / 乌木 匹配
        messages_woody = [{"role": "user", "content": "I like woody fragrance and extra 沉香 or 乌木"}]
        res_woody = await openai_p.chat(messages_woody)
        assert "沉香" in res_woody or "乌木" in res_woody
        
        # 提取 json 并验证 changed 属性
        match = re.search(r"```json\n(.*?)\n```", res_woody, re.DOTALL)
        assert match is not None
        data_woody = json.loads(match.group(1))
        assert "updated_plans" in data_woody
        updated_plans = data_woody["updated_plans"]
        assert len(updated_plans) > 0
        plan = updated_plans[0]
        assert plan["category"] == "花香木质调"
        # 验证 base_notes 包含 changed=True 标记
        changed_notes = [note for note in plan["base_notes"] if note.get("changed") is True]
        assert len(changed_notes) > 0
        assert any(n["name"] == "沉香" for n in changed_notes)
        assert any(n["name"] == "乌木" for n in changed_notes)

        # 2. 验证 grapefruit / 葡萄柚 匹配
        messages_grapefruit = [{"role": "user", "content": "Please change top note to grapefruit 葡萄柚"}]
        res_grapefruit = await openai_p.chat(messages_grapefruit)
        assert "葡萄柚" in res_grapefruit
        
        match_gf = re.search(r"```json\n(.*?)\n```", res_grapefruit, re.DOTALL)
        assert match_gf is not None
        data_gf = json.loads(match_gf.group(1))
        updated_plans_gf = data_gf["updated_plans"]
        assert len(updated_plans_gf) > 0
        plan_gf = updated_plans_gf[0]
        # 验证 top_notes 包含 changed=True 且包含 葡萄柚 (Grapefruit)
        changed_top_notes = [note for note in plan_gf["top_notes"] if note.get("changed") is True]
        assert len(changed_top_notes) > 0
        assert any("葡萄柚" in n["name"] for n in changed_top_notes)

        # 3. 验证 cedarwood / 雪松 匹配
        messages_cedar = [{"role": "user", "content": "I want cedarwood 雪松 as the base note"}]
        res_cedar = await openai_p.chat(messages_cedar)
        assert "雪松" in res_cedar
        
        match_cd = re.search(r"```json\n(.*?)\n```", res_cedar, re.DOTALL)
        assert match_cd is not None
        data_cd = json.loads(match_cd.group(1))
        updated_plans_cd = data_cd["updated_plans"]
        assert len(updated_plans_cd) > 0
        plan_cd = updated_plans_cd[0]
        # 验证 base_notes 包含 changed=True 且包含 雪松 (Cedarwood)
        changed_base_notes = [note for note in plan_cd["base_notes"] if note.get("changed") is True]
        assert len(changed_base_notes) > 0
        assert any("雪松" in n["name"] for n in changed_base_notes)

        # 4. 验证 emotional / 情绪 匹配
        messages_emotional = [{"role": "user", "content": "Tell me about emotional benefits"}]
        res_emotional = await openai_p.chat(messages_emotional)
        assert "柠檬烯" in res_emotional
        assert "多巴胺" in res_emotional
        assert "情绪价值" in res_emotional

    @pytest.mark.asyncio
    async def test_mock_vision_data_structure(self):
        openai_p = OpenAIProvider(api_key=None)
        glm_p = GLMProvider(api_key=None)

        # 单张图片分析
        res_single = await openai_p.vision(image_paths=["/path/to/img1.jpg"], prompt="Analyze style")
        data_single = json.loads(res_single)
        assert isinstance(data_single, dict)
        assert "穿搭单品" in data_single
        assert "搜索关键词" in data_single
        assert "消费水平" in data_single
        assert "生活方式/审美倾向" in data_single

        # 组图分析 (多张图片)
        res_multi = await glm_p.vision(image_paths=["/path/to/img1.jpg", "/path/to/img2.jpg"], prompt="Compare style")
        data_multi = json.loads(res_multi)
        assert isinstance(data_multi, list)
        assert len(data_multi) == 2
        for item in data_multi:
            assert "穿搭风格" in item
            assert "人物/主题" in item
            assert "消费水平" in item

        # 组图分析 (Prompt 包含 "grid")
        res_grid = await openai_p.vision(image_paths=["/path/to/img1.jpg"], prompt="Show a grid analysis")
        data_grid = json.loads(res_grid)
        assert isinstance(data_grid, list)
