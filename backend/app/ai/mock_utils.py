import os
import re
import json
from pathlib import Path
from app.config import settings

def load_mock_file(filename: str) -> str:
    """从 tests 目录加载 Mock JSON 数据，若不存在则返回 fallback 结构。"""
    base_dir = settings.BASE_DIR
    paths = [
        base_dir / "tests" / "e2e" / "mock_data" / filename,
        base_dir / "tests" / "mock_data" / filename,
        base_dir.parent / "backend" / "tests" / "e2e" / "mock_data" / filename,
    ]
    for p in paths:
        if p.exists():
            with open(p, "r", encoding="utf-8") as f:
                return f.read()
                
    # Fallback default mock data if files are not present
    if filename == "iceberg_analysis.json":
        return json.dumps({
            "surface": "显性行为层：甜美系穿搭、粉色系偏好、圈层社交（同好会/茶会）、种草型消费路径，这些指向了一个高度视觉化、注重外在形象表达的用户群体。",
            "middle": "情感价值层：情绪需求驱动的消费动机，拍照出片和约会社交的场景需求，反映了这个群体通过「穿搭-拍照-分享」的闭环来获得自我认同和社交认可。香水在这里是「完整look的最后一笔」。",
            "deep": "深层需求：在亚文化穿搭的表象下，是对「理想化自我」的持续构建。她们通过精致的外在包装来回应内心对美好、浪漫、被重视的渴望。香水不仅是装饰，更是一种「穿上另一个自己」的仪式感。"
        }, ensure_ascii=False)
    elif filename == "fragrance_recommendation.json":
        return json.dumps([
            {
                "plan_id": "plan_1",
                "name": "粉色之梦 — 花果甜香",
                "category": "花果香调",
                "top_notes": [
                    {"name": "佛手柑", "description": "明亮清新的开场", "reason": "呼应粉色系审美中的活力感"},
                    {"name": "粉红胡椒", "description": "微辣的甜蜜点缀", "reason": "匹配甜美系风格中的俏皮元素"}
                ],
                "middle_notes": [
                    {"name": "鸢尾花", "description": "粉质的优雅花香", "reason": "连接古典系审美与蓝紫色偏好"},
                    {"name": "玫瑰", "description": "经典的浪漫花香", "reason": "呼应约会社交场景的浪漫需求"}
                ],
                "base_notes": [
                    {"name": "白檀", "description": "温柔的木质收尾", "reason": "提供内陆文化圈熟悉的东方感"},
                    {"name": "香草", "description": "甜蜜的温暖基调", "reason": "满足情绪需求中的安全感和愉悦"}
                ],
                "recommendation_reason": "这个方案直接呼应了目标群体的甜美系穿搭偏好和粉色系色彩倾向。前调的佛手柑和粉红胡椒创造了活泼甜蜜的第一印象，适合种草型消费者的「第一嗅」冲击。中调的鸢尾花和玫瑰兼顾了古典系的优雅和约会场景的浪漫氛围。后调的白檀和香草提供了温暖的收尾，呼应了内陆文化圈对东方香调的天然亲近感，同时满足了情绪需求中对「被温柔包裹」的深层渴望。",
                "fragrance_story": "她在镜子前最后确认了蝴蝶结的位置。今天是同好会的茶会，她选了那条粉色的洛丽塔裙。出门前，她在手腕上按下最后一个仪式——喷雾升起，先是一阵清亮的柑橘，像推开花园门的那一刻。然后是粉质的花香缓缓展开，像那些她反复截图收藏的少女漫画场景。等到傍晚，只剩下贴着皮肤的温暖甜香，是她给自己的、属于今天的奖励。",
                "iceberg_analysis": {
                    "surface": "显性行为层：甜美系穿搭、粉色系偏好、圈层社交（同好会/茶会）、种草型消费路径，这些指向了一个高度视觉化、注重外在形象表达的用户群体。",
                    "middle": "情感价值层：情绪需求驱动的消费动机，拍照出片和约会社交的场景需求，反映了这个群体通过「穿搭-拍照-分享」的闭环来获得自我认同和社交认可。香水在这里是「完整look的最后一笔」。",
                    "deep": "深层需求：在亚文化穿搭的表象下，是对「理想化自我」的持续构建。她们通过精致的外在包装来回应内心对美好、浪漫、被重视的渴望。香水不仅是装饰，更是一种「穿上另一个自己」的仪式感。"
                }
            },
            {
                "plan_id": "plan_2",
                "name": "紫色回廊 — 东方花香",
                "category": "东方花香调",
                "top_notes": [],
                "middle_notes": [],
                "base_notes": [],
                "recommendation_reason": "...",
                "fragrance_story": "...",
                "iceberg_analysis": {}
            },
            {
                "plan_id": "plan_3",
                "name": "林间晨曦 — 绿意木质",
                "category": "木质香调",
                "top_notes": [],
                "middle_notes": [],
                "base_notes": [],
                "recommendation_reason": "...",
                "fragrance_story": "...",
                "iceberg_analysis": {}
            }
        ], ensure_ascii=False)
    return "{}"

def handle_mock_chat(messages: list[dict]) -> str:
    """根据最新一轮的用户消息以及包含的关键词，返回模拟的文本和 JSON 块。"""
    user_message = ""
    for m in reversed(messages):
        if m.get("role") == "user":
            user_message = m.get("content", "")
            break

    if isinstance(user_message, list):
        text_parts = []
        for part in user_message:
            if isinstance(part, dict) and part.get("type") == "text":
                text_parts.append(part.get("text", ""))
        user_message = "\n".join(text_parts)

    user_message_lower = user_message.lower()

    # 1. 判定是否为初次生成香调推荐请求
    is_reasoning = any(kw in user_message_lower for kw in ["selected_tags", "冰山", "iceberg", "推荐", "plan_count"])
    if is_reasoning:
        # 匹配要求的 plan_count 数量
        plan_count = 3
        count_match = re.search(r'(\d+)\s*(?:套|plans?)', user_message_lower)
        if count_match:
            plan_count = int(count_match.group(1))

        rec_data = json.loads(load_mock_file("fragrance_recommendation.json"))
        iceberg_data = json.loads(load_mock_file("iceberg_analysis.json"))

        response_json = {
            "iceberg_analysis": iceberg_data,
            "recommendations": rec_data[:plan_count]
        }
        return f"```json\n{json.dumps(response_json, ensure_ascii=False)}\n```"

    # 2. 判定是否为微调对话请求 - 匹配关键词
    # 2.1 沉香 / 乌木 / woody
    if any(kw in user_message_lower for kw in ["wood", "沉香", "乌木"]):
        rec_data = json.loads(load_mock_file("fragrance_recommendation.json"))
        plan1 = rec_data[0].copy()
        plan1["category"] = "花香木质调"
        plan1["base_notes"] = [
            {"name": "沉香", "description": "深沉的东方木质", "reason": "增加神秘感和深度，呼应哥特系偏好", "changed": True},
            {"name": "乌木", "description": "烟熏的暗色木质", "reason": "与粉色系形成「甜美×暗黑」的反差张力", "changed": True}
        ]
        plan1["recommendation_reason"] = "修改后的方案保留了花果甜美的前中调，但通过沉香和乌木的后调创造了一个戏剧性的反转..."
        
        updated_plans = [plan1]
        reply = "好的，我理解你希望增加方案一的深度和层次感。将后调从白檀+香草替换为沉香+乌木是一个很好的方向——这会让整体从「甜美少女」转向「甜美中带暗黑」的风格。"
        return f"{reply}\n```json\n{{\"updated_plans\": {json.dumps(updated_plans, ensure_ascii=False)}}}\n```"

    # 2.2 葡萄柚 / grapefruit
    if any(kw in user_message_lower for kw in ["grapefruit", "葡萄柚"]):
        rec_data = json.loads(load_mock_file("fragrance_recommendation.json"))
        plan1 = rec_data[0].copy()
        plan1["top_notes"] = [
            {"name": "葡萄柚 (Grapefruit)", "description": "微酸微涩的柑橘香", "reason": "带来更多活力", "changed": True},
            {"name": "粉红胡椒", "description": "微辣的甜蜜点缀", "reason": "匹配甜美系风格中的俏皮元素"}
        ]
        updated_plans = [plan1]
        reply = "已为您将方案一的前调更新为葡萄柚以提供更多活力感。"
        return f"{reply}\n```json\n{{\"updated_plans\": {json.dumps(updated_plans, ensure_ascii=False)}}}\n```"

    # 2.3 雪松 / cedarwood
    if any(kw in user_message_lower for kw in ["cedarwood", "雪松"]):
        rec_data = json.loads(load_mock_file("fragrance_recommendation.json"))
        plan1 = rec_data[0].copy()
        plan1["base_notes"] = [
            {"name": "雪松 (Cedarwood)", "description": "干净挺拔的木香", "reason": "提供温暖干燥的支持", "changed": True},
            {"name": "香草", "description": "甜蜜的温暖基调", "reason": "满足情绪需求中的安全感和愉悦"}
        ]
        updated_plans = [plan1]
        reply = "好的，已在方案一的后调中加入雪松以提供更干净挺拔的木质气息。"
        return f"{reply}\n```json\n{{\"updated_plans\": {json.dumps(updated_plans, ensure_ascii=False)}}}\n```"

    # 2.4 情绪 / emotional
    if any(kw in user_message_lower for kw in ["emotional", "情绪"]):
        return "葡萄柚的香气含有丰富的柠檬烯，能够刺激大脑分泌多巴胺，缓解焦虑，带来积极振奋的情绪价值。"

    # 默认 Mock 文本回复
    return "收到您的反馈，我已经理解您的想法，并为您记录下了微调建议。"

def handle_mock_vision(image_paths: list[str], prompt: str) -> str:
    """视觉分析 Mock 返回"""
    if len(image_paths) > 1 or "grid" in prompt.lower():
        # 组图分析结果
        mock_result = [
            {"穿搭风格": "甜美系", "人物/主题": "洛丽塔少女", "消费水平": "中偏高"},
            {"穿搭风格": "古典系", "人物/主题": "汉服同好", "消费水平": "中等"}
        ]
    else:
        # 单张图封面分析结果
        mock_result = {
            "穿搭单品": ["粉色连衣裙", "蕾丝发卡"],
            "搜索关键词": ["甜美洛丽塔", "约会穿搭"],
            "场景和城市线索": "拍照出片、一线城市咖啡馆",
            "消费水平": "中高消费",
            "生活方式/审美倾向": "精致生活、重度视觉化分享"
        }
    return json.dumps(mock_result, ensure_ascii=False)
