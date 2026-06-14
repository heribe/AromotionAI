"""
Fragrance recommendation engine abstract base class.

定义推荐引擎的统一接口，便于后续切换到 Dify 工作流或本地 Agent。
M5 第一版仅实现 PromptFragranceEngine（见 prompt_engine.py）。

R2 Three-Question Self-Check:
1. Contract Closure: 两个抽象方法对应 §2.1 generate 与 §2.2 chat 的核心
   AI 调用契约；返回值结构固定，service 层据此做后续持久化。
2. Symmetry: 纯抽象接口，无资源分配；子类负责 provider 调用与 JSON 解析。
3. External Timing: 异步方法签名，调用方负责重试与超时控制。
"""

from abc import ABC, abstractmethod


class FragranceEngine(ABC):
    """香调推荐引擎基类（§6.1）。"""

    @abstractmethod
    async def generate(
        self,
        fused_profile: str,
        selected_tags: dict,
        plan_count: int = 3,
    ) -> dict:
        """生成推荐方案。

        Args:
            fused_profile: 已按权重融合的博主+粉丝画像文本。
            selected_tags: 调香师筛选后的标签集合。
            plan_count: 方案数量。

        Returns:
            dict: 形如 ``{"iceberg_analysis": {surface,middle,deep},
            "recommendations": [FragrancePlan...]}``。
        """
        ...

    @abstractmethod
    async def chat(
        self,
        history: list[dict],
        current_plans: list[dict],
        user_message: str,
        selected_tags: dict,
    ) -> tuple[str, list[dict] | None]:
        """对话微调。

        Args:
            history: 最近 MAX_HISTORY_MESSAGES 条对话（role/content）。
            current_plans: 当前 session 的方案列表（用于上下文）。
            user_message: 调香师本轮输入。
            selected_tags: session 的标签集合（注入 system prompt）。

        Returns:
            (reply_text, updated_plans | None)。updated_plans 仅包含被修改的方案。
        """
        ...
