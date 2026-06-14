"""
Fragrance recommendation engine registry and factory.

M5 第一版仅注册 "prompt" 引擎。后续接入 Dify / 本地 Agent 的步骤见
docs/superpowers/specs/2026-06-14-fragrance-engine-design.md §7
与 docs/03-part2-backend.md §6.1 的"后续接入说明"。
"""

from app.engines.base import FragranceEngine
from app.engines.prompt_engine import PromptFragranceEngine

# 引擎注册表。后续接入：
#   "dify": DifyFragranceEngine,        # 见设计文档 §7
#   "local_agent": LocalAgentFragranceEngine,
ENGINE_REGISTRY: dict[str, type[FragranceEngine]] = {
    "prompt": PromptFragranceEngine,
}


def get_engine(engine_type: str = "prompt") -> FragranceEngine:
    """按类型获取引擎实例。未知类型回退到 prompt（第一版唯一实现）。"""
    cls = ENGINE_REGISTRY.get(engine_type, PromptFragranceEngine)
    return cls()


__all__ = [
    "FragranceEngine",
    "PromptFragranceEngine",
    "ENGINE_REGISTRY",
    "get_engine",
]
