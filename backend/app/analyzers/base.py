import re
import json
import logging
from app.ai import ai_registry, AIRegistry, AIProvider

logger = logging.getLogger(__name__)

class BaseAnalyzer:
    """AI 分析器基类"""

    def __init__(self, registry: AIRegistry = None):
        """
        初始化 AI 分析器
        
        Args:
            registry: AI 提供者注册表实例，如果未提供则使用全局的 ai_registry。
        """
        self.registry = registry or ai_registry

    def _get_provider_for_slot(self, slot_id: str) -> tuple[AIProvider, str]:
        """
        获取槽位绑定的提供者实例和模型名称
        
        Args:
            slot_id: 槽位 ID，如 "visual_analysis" 或 "comment_analysis"
            
        Returns:
            tuple[AIProvider, str]: 提供者实例与模型名称
        """
        return self.registry.get_provider_for_slot(slot_id)

    def parse_json_safely(self, text: str, default_fallback: dict | list) -> dict | list:
        """
        安全的 JSON 响应提取与防呆解析。
        能够应对 AI 返回 Markdown 代码块、带有说明文字、只返回部分 JSON 等异常场景，
        并在解析失败时返回合法的默认降级字典/列表。
        
        Args:
            text: AI 返回的原始文本响应
            default_fallback: 默认降级返回值（可以是 dict 或 list）
            
        Returns:
            dict | list: 解析后的 JSON 对象或 default_fallback
        """
        if not text:
            return default_fallback

        text_clean = text.strip()

        # 1. 尝试直接整段解析
        try:
            return json.loads(text_clean)
        except json.JSONDecodeError:
            pass

        # 2. 尝试正则匹配 ```json ... ``` 包裹的代码块
        json_block_match = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL | re.IGNORECASE)
        if json_block_match:
            try:
                return json.loads(json_block_match.group(1).strip())
            except json.JSONDecodeError:
                pass

        # 3. 尝试正则匹配 ``` ... ``` 包裹的代码块
        code_block_match = re.search(r"```\s*(.*?)\s*```", text, re.DOTALL)
        if code_block_match:
            try:
                return json.loads(code_block_match.group(1).strip())
            except json.JSONDecodeError:
                pass

        # 4. 尝试正则提取最外层的大括号 {...} 或中括号 [...] 结构
        if isinstance(default_fallback, list):
            array_match = re.search(r"(\[.*\])", text, re.DOTALL)
            if array_match:
                try:
                    return json.loads(array_match.group(1).strip())
                except json.JSONDecodeError:
                    pass
        else:
            dict_match = re.search(r"(\{.*\})", text, re.DOTALL)
            if dict_match:
                try:
                    return json.loads(dict_match.group(1).strip())
                except json.JSONDecodeError:
                    pass

        # 5. 如果类型匹配没有成功，做交叉类型提取兜底
        if not isinstance(default_fallback, list):
            dict_match = re.search(r"(\{.*\})", text, re.DOTALL)
            if dict_match:
                try:
                    return json.loads(dict_match.group(1).strip())
                except json.JSONDecodeError:
                    pass
        else:
            array_match = re.search(r"(\[.*\])", text, re.DOTALL)
            if array_match:
                try:
                    return json.loads(array_match.group(1).strip())
                except json.JSONDecodeError:
                    pass

        logger.warning(
            f"Failed to safely parse JSON from AI response. Returning default fallback. "
            f"Original text segment: {text[:200]}..."
        )
        return default_fallback
