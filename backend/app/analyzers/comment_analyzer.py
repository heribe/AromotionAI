import logging
from app.analyzers.base import BaseAnalyzer

logger = logging.getLogger(__name__)

class CommentAnalyzer(BaseAnalyzer):
    """评论分析器，负责分析社交媒体评论数据"""

    async def analyze_comments(self, comments: list[dict]) -> dict:
        """
        分析这批评论文本并输出结构化统计指标
        
        Args:
            comments: 包含评论详情的 dict 列表，每条评论结构包含 text、ip_label 等字段。
            
        Returns:
            dict: 包含关键词频次、情感分布、购买意图、方言/梗特征、互动类型分布的分析结果
        """
        fallback = {
            "keyword_stats": {},
            "sentiment_distribution": {
                "positive": 0.0,
                "neutral": 0.0,
                "negative": 0.0
            },
            "purchase_intent": {
                "level": "中",
                "signals": []
            },
            "dialect_features": {
                "slang": [],
                "dialects": []
            },
            "interaction_type": {
                "question": 0.0,
                "praise": 0.0,
                "complaint": 0.0,
                "other": 0.0
            }
        }

        if not comments:
            return fallback

        # 格式化拼接评论文本（兼容字段缺失或为 None 的情况）
        formatted_comments = []
        for idx, comment in enumerate(comments):
            text = (comment.get("text") or "").strip()
            ip_label = (comment.get("ip_label") or "").strip()
            if text:
                line = f"评论 {idx+1}: {text}"
                if ip_label:
                    line += f" (IP归属地: {ip_label})"
                formatted_comments.append(line)

        comments_payload = "\n".join(formatted_comments)

        if not comments_payload:
            return fallback

        provider, model_name = self._get_provider_for_slot("comment_analysis")

        prompt = (
            "请分析以下社交媒体的评论数据，并返回结构化的分析结果。\n"
            "你需要评估评论的主题、情感态度、购买意愿以及语言特色等。\n\n"
            "评论数据：\n"
            f"{comments_payload}\n\n"
            "请严格按照以下 JSON 格式输出，不要包含任何额外的 Markdown 以外的说明文字，直接返回 JSON 代码块：\n"
            "{\n"
            '  "keyword_stats": {"关键词1": 频次1, "关键词2": 频次2},\n'
            '  "sentiment_distribution": {\n'
            '    "positive": 正向情感比例(0.0到1.0之间的浮点数),\n'
            '    "neutral": 中性情感比例(0.0到1.0之间的浮点数),\n'
            '    "negative": 负向情感比例(0.0到1.0之间的浮点数)\n'
            "  },\n"
            '  "purchase_intent": {\n'
            '    "level": "购买意图强弱级别，可选值：低、中、高",\n'
            '    "signals": ["购买意图信号词/特征词1", "购买意图信号词/特征词2"]\n'
            "  },\n"
            '  "dialect_features": {\n'
            '    "slang": ["网络梗或网络流行语1", "网络梗或网络流行语2"],\n'
            '    "dialects": ["使用的方言/地域词汇1", "使用的方言/地域词汇2"]\n'
            "  },\n"
            '  "interaction_type": {\n'
            '    "question": 提问型占比(0.0到1.0),\n'
            '    "praise": 赞赏型占比(0.0到1.0),\n'
            '    "complaint": 吐槽/抱怨型占比(0.0到1.0),\n'
            '    "other": 其他占比(0.0到1.0)\n'
            "  }\n"
            "}"
        )

        messages = [
            {"role": "user", "content": prompt}
        ]

        try:
            raw_res = await provider.chat(
                messages=messages,
                model=model_name
            )
            result = self.parse_json_safely(raw_res, fallback)

            # 确保契约闭环：填充缺少的顶级键与子键
            if isinstance(result, dict):
                # 1. 检查一级字段
                for k, v in fallback.items():
                    if k not in result:
                        result[k] = v
                
                # 2. 检查二级字段（对 dict 类型的字段做深度检查）
                for sub_key in ["sentiment_distribution", "purchase_intent", "dialect_features", "interaction_type"]:
                    if not isinstance(result[sub_key], dict):
                        result[sub_key] = fallback[sub_key]
                    else:
                        # 确保二级字段中包含所有必填键
                        for k, v in fallback[sub_key].items():
                            if k not in result[sub_key]:
                                result[sub_key][k] = v
                                
                return result
            return fallback

        except Exception as e:
            logger.error(f"Error in analyze_comments: {e}", exc_info=True)
            return fallback
