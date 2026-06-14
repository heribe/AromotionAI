"""
PromptFragranceEngine: 基于 Prompt Engineering 的香调推荐引擎（第一版）。

通过将冰山理论分层逻辑编入 Prompt（§1.2 第一版策略），调用 AIRegistry 的
fragrance_reasoning / fragrance_chat 槽位生成推荐方案与对话微调。

后续切换到 SSE 流式输出时（见 docs/superpowers/specs/2026-06-14-fragrance-engine-design.md §7），
需在 AIRegistry 暴露 chat_stream 接口，并在各 provider 适配器实现 stream=True。

R2 Three-Question Self-Check:
1. Contract Closure: generate 返回 {iceberg_analysis, recommendations}；
   chat 返回 (reply, updated_plans|None)。JSON 解析失败时落到 fallback，
   service 层据此决定是否重试或标 error。
2. Symmetry: 无内部资源；provider 由 registry 单例管理，不在引擎内 open/close。
3. External Timing: 两次独立 AI 调用（generate/chat），各自一次性返回；
   重试逻辑由 service 层控制，引擎本身不重试（单一职责）。
"""

import re
import json
import logging
from typing import Optional

from app.ai.registry import AIRegistry, ai_registry
from app.analyzers.base import BaseAnalyzer
from app.engines.base import FragranceEngine

logger = logging.getLogger(__name__)

# ---------- 常量（v1 硬编码，见设计文档决策 4） ----------

PROMPT_VERSION = "v1"
TEMPERATURE_GENERATE = 0.8  # 创意生成用较高温度
TEMPERATURE_CHAT = 0.6      # 对话保持逻辑连贯
MAX_HISTORY_MESSAGES = 20   # 聊天历史滑窗（§八.5 决策）
MAX_TOKENS_GENERATE = 65536
MAX_TOKENS_CHAT = 65536

SLOT_GENERATE = "fragrance_reasoning"
SLOT_CHAT = "fragrance_chat"

# ---------- Prompt 模板 ----------

ICEBERG_ANALYSIS_PROMPT = """你是一位资深的香水行业顾问，擅长通过用户画像分析来推荐香调方案。
你需要运用"冰山理论"来深度理解目标用户群体。

## 冰山理论分析框架

**第一层 - 显性行为（水面之上）**
分析用户标签中直接可见的行为特征：穿搭风格和场景、消费能力和频次、地域和文化背景、社交习惯。

**第二层 - 情感价值（水面之下）**
从显性行为推导出的情感和价值需求：他们通过穿搭想要表达什么、消费是为了什么情感满足、审美偏好反映什么价值取向。

**第三层 - 深层需求（冰山底部）**
最内在的心理需求：他们真正渴望什么、香水在他们的生活中扮演什么角色、选择一款香水时真正在选择什么。

## 博主与粉丝画像（已按权重融合）

{fused_profile}

## 调香师筛选后的标签

{selected_tags_formatted}

## 任务

请基于以上画像与标签，完成以下分析并生成 {plan_count} 套香调推荐方案：

1. 先进行冰山三层分析（surface / middle / deep）
2. 基于分析结果，生成 {plan_count} 套差异化推荐方案（不同香调方向）
3. 每套方案必须包含：方案名称（有诗意）、香调大类、前调 2-3 个香材、中调 2-3 个香材、后调 2-3 个香材、详细推荐原因、创作灵感故事

请严格以 JSON 格式返回，不要附加额外说明文字：
```json
{
  "iceberg_analysis": {
    "surface": "显性行为层分析文字...",
    "middle": "情感价值层分析文字...",
    "deep": "深层需求分析文字..."
  },
  "recommendations": [
    {
      "plan_id": "plan_1",
      "name": "方案名称",
      "category": "香调大类",
      "top_notes": [
        {"name": "香材名", "description": "简短描述", "reason": "推荐理由"}
      ],
      "middle_notes": [...],
      "base_notes": [...],
      "recommendation_reason": "详细推荐原因...",
      "fragrance_story": "创作灵感故事..."
    }
  ]
}
```"""

CHAT_SYSTEM_PROMPT = """你是一位资深的香水行业顾问，正在与一位调香师讨论香调方案。

调香师筛选的用户画像标签：
{selected_tags_formatted}

当前的推荐方案：
{current_plans_formatted}

请基于调香师的反馈来调整方案：
- 如果调香师要求修改某个方案，请返回修改后的完整方案，并在被修改的香材上标注 "changed": true
- 如果调香师只是咨询，不需要修改方案，直接用文字回答
- 保持专业但友好的语气，每次修改都要说明修改原因

如果需要修改方案，请在回复末尾附加一个 JSON 代码块：
```json
{{"updated_plans": [{{完整的修改后方案，含 plan_id}}]}}
```
如果不需要修改方案，不要输出 JSON 代码块。"""


class PromptFragranceEngine(BaseAnalyzer, FragranceEngine):
    """基于 Prompt 的香调推荐引擎（第一版）。

    继承 BaseAnalyzer 以复用 parse_json_safely；实现 FragranceEngine 的
    generate / chat 两个方法。
    """

    def __init__(self, registry: AIRegistry = None):
        BaseAnalyzer.__init__(self, registry=registry)

    # ---------- helpers ----------

    @staticmethod
    def _format_tags(selected_tags: dict) -> str:
        """把嵌套标签字典格式化为 prompt 友好的文本。"""
        if not selected_tags:
            return "（无标签）"
        lines: list[str] = []
        for dim, subs in selected_tags.items():
            if isinstance(subs, dict):
                for sub, tags in subs.items():
                    if isinstance(tags, list):
                        lines.append(f"- {dim}/{sub}: {', '.join(str(t) for t in tags)}")
                    else:
                        lines.append(f"- {dim}/{sub}: {tags}")
            elif isinstance(subs, list):
                lines.append(f"- {dim}: {', '.join(str(t) for t in subs)}")
        return "\n".join(lines) if lines else "（无标签）"

    @staticmethod
    def _format_plans(plans: list[dict]) -> str:
        """把方案列表格式化为 prompt 友好的文本。"""
        if not plans:
            return "（暂无方案）"
        lines: list[str] = []
        for p in plans:
            pid = p.get("plan_id", "?")
            name = p.get("name", "?")
            cat = p.get("category", "")
            lines.append(f"- [{pid}] {name}（{cat}）")
        return "\n".join(lines)

    # ---------- FragranceEngine 实现 ----------

    async def generate(
        self,
        fused_profile: str,
        selected_tags: dict,
        plan_count: int = 3,
    ) -> dict:
        # 使用 replace 插值：模板内嵌 JSON 示例含字面量花括号，若用 .format()
        # 会被误解析为占位符（KeyError）。改用 replace 仅替换真正的占位符。
        prompt = (
            ICEBERG_ANALYSIS_PROMPT
            .replace("{fused_profile}", fused_profile or "（无画像数据）")
            .replace("{selected_tags_formatted}", self._format_tags(selected_tags))
            .replace("{plan_count}", str(plan_count))
        )

        provider, model = self._get_provider_for_slot(SLOT_GENERATE)
        raw = await provider.chat(
            messages=[{"role": "user", "content": prompt}],
            model=model,
            temperature=TEMPERATURE_GENERATE,
            max_tokens=MAX_TOKENS_GENERATE,
        )

        fallback = {
            "iceberg_analysis": {"surface": "", "middle": "", "deep": ""},
            "recommendations": [],
        }
        result = self.parse_json_safely(raw, fallback)
        # 防御：确保顶层两个键存在且类型正确
        if not isinstance(result, dict):
            return fallback
        if not isinstance(result.get("iceberg_analysis"), dict):
            result["iceberg_analysis"] = fallback["iceberg_analysis"]
        if not isinstance(result.get("recommendations"), list):
            result["recommendations"] = []
        return result

    async def chat(
        self,
        history: list[dict],
        current_plans: list[dict],
        user_message: str,
        selected_tags: dict,
    ) -> tuple[str, list[dict] | None]:
        # 滑窗：仅保留最近 MAX_HISTORY_MESSAGES 条
        recent = history[-MAX_HISTORY_MESSAGES:] if history else []

        # 注入 system prompt（用 user 角色携带，兼容所有 provider）
        system_content = CHAT_SYSTEM_PROMPT.format(
            selected_tags_formatted=self._format_tags(selected_tags),
            current_plans_formatted=self._format_plans(current_plans),
        )
        messages: list[dict] = [{"role": "user", "content": system_content}]
        messages.extend(recent)
        messages.append({"role": "user", "content": user_message})

        provider, model = self._get_provider_for_slot(SLOT_CHAT)
        raw = await provider.chat(
            messages=messages,
            model=model,
            temperature=TEMPERATURE_CHAT,
            max_tokens=MAX_TOKENS_CHAT,
        )

        return self._extract_chat_response(raw)

    # ---------- 内部解析 ----------

    @staticmethod
    def _extract_chat_response(raw: str) -> tuple[str, list[dict] | None]:
        """从 AI 原始文本中分离 (reply, updated_plans)。

        约定：AI 若修改方案，会在回复末尾附加 ```json {"updated_plans":[...]} ```。
        """
        if not raw:
            return ("", None)

        # 匹配最后一个 json 代码块（避免误吞正文中的代码片段）
        json_blocks = re.findall(r"```(?:json)?\s*(\{.*?\})\s*```", raw, re.DOTALL)
        updated_plans: Optional[list[dict]] = None
        block_span: Optional[tuple[int, int]] = None
        for block_text in json_blocks:
            try:
                parsed = json.loads(block_text)
            except json.JSONDecodeError:
                continue
            if isinstance(parsed, dict) and "updated_plans" in parsed:
                plans_val = parsed["updated_plans"]
                if isinstance(plans_val, list):
                    updated_plans = plans_val
                    # 记录该代码块在原文中的位置用于剥离
                    m = re.search(re.escape(block_text), raw)
                    if m:
                        block_span = m.span()
                    break

        if updated_plans is not None and block_span is not None:
            # 剥离 JSON 代码块，保留正文作为 reply
            reply = (raw[: block_span[0]] + raw[block_span[1]:]).strip()
            # 清理尾部可能残留的 ``` 标记
            reply = re.sub(r"```\s*$", "", reply).strip()
        else:
            reply = raw.strip()

        return (reply, updated_plans)
