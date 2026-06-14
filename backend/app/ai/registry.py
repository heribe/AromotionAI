import os
import threading
from .base import AIProvider
from .provider_glm import GLMProvider
from .provider_openai import OpenAIProvider
from .provider_deepseek import DeepSeekProvider

class AIRegistry:
    """AI Slot Binding and Provider Registry"""

    def __init__(self):
        self._lock = threading.RLock()
        self._providers: dict[str, AIProvider] = {}
        self._slots: dict[str, tuple[str, str]] = {}

        # 默认注册三大提供者
        self.register_provider("glm", GLMProvider())
        self.register_provider("openai", OpenAIProvider())
        self.register_provider("deepseek", DeepSeekProvider())

        # 模型名可通过环境变量配置，以适配不同套餐。
        # 未配置时默认使用 glm-5.2（Coding Plan）；标准套餐可设 GLM_MODEL=glm-4。
        _glm_text_model = os.getenv("GLM_MODEL", "glm-5.2")
        # 视觉槽位必须用支持多模态的 glm-4.6v（glm-5.2 是纯文本模型，不支持 vision）
        _glm_vision_model = os.getenv("GLM_VISION_MODEL", "glm-4.6v")

        # 默认 Slot 绑定
        # 槽位包含: visual_analysis, comment_analysis, tag_aggregation, fragrance_reasoning, fragrance_chat, analysis_task
        self.bind_slot("visual_analysis", "glm", _glm_vision_model)
        self.bind_slot("comment_analysis", "glm", _glm_text_model)
        self.bind_slot("tag_aggregation", "glm", _glm_text_model)
        self.bind_slot("fragrance_reasoning", "glm", _glm_text_model)
        self.bind_slot("fragrance_chat", "glm", _glm_text_model)
        self.bind_slot("analysis_task", "glm", _glm_text_model)

    def register_provider(self, name: str, provider: AIProvider) -> None:
        """注册 AI 提供者"""
        with self._lock:
            if not isinstance(provider, AIProvider):
                raise TypeError("provider must be an instance of AIProvider")
            self._providers[name] = provider

    def get_provider(self, name: str) -> AIProvider:
        """获取注册的 AI 提供者"""
        with self._lock:
            if name not in self._providers:
                raise ValueError(f"AI Provider '{name}' is not registered.")
            return self._providers[name]

    def bind_slot(self, slot_id: str, provider_name: str, model_name: str) -> None:
        """绑定槽位到指定的提供者和模型"""
        with self._lock:
            if provider_name not in self._providers:
                raise ValueError(f"AI Provider '{provider_name}' must be registered before binding to slot.")
            provider = self._providers[provider_name]
            if slot_id == "visual_analysis" and not provider.supports_vision:
                raise ValueError(f"AI Provider '{provider_name}' does not support vision capability for slot 'visual_analysis'")
            self._slots[slot_id] = (provider_name, model_name)

    def get_provider_for_slot(self, slot_id: str) -> tuple[AIProvider, str]:
        """获取槽位绑定的提供者实例和模型名称"""
        with self._lock:
            if slot_id not in self._slots:
                raise ValueError(f"AI Slot '{slot_id}' is not bound.")
            provider_name, model_name = self._slots[slot_id]
            provider = self.get_provider(provider_name)
            return provider, model_name

# 导出全局单例
ai_registry = AIRegistry()
