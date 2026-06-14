from abc import ABC, abstractmethod
import json

class AIProvider(ABC):
    """AI Provider Base Class"""

    def is_mock_mode(self) -> bool:
        """是否处于 Mock 模式"""
        return self._is_mock_mode()

    def _is_mock_mode(self) -> bool:
        return False

    async def chat(self, messages: list[dict], **kwargs) -> str:
        """文本对话接口

        Args:
            messages: 消息列表，每个消息是一个 dict，如 {"role": "user", "content": "..."}
            **kwargs: 其他调用参数

        Returns:
            str: 模型生成的文本回复
        """
        raise NotImplementedError("chat method not implemented")

    async def vision(self, image_paths: list[str], prompt: str, **kwargs) -> str:
        """视觉分析接口

        Args:
            image_paths: 本地图片路径列表
            prompt: 提示词
            **kwargs: 其他调用参数

        Returns:
            str: 模型生成的分析文本
        """
        raise NotImplementedError("vision method not implemented")

    def _encode_image_to_data_uri(self, image_path: str) -> str:
        """将本地图片转为 Data URI 格式"""
        import base64
        import os
        import mimetypes
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image not found at {image_path}")
        mime_type, _ = mimetypes.guess_type(image_path)
        if not mime_type:
            mime_type = "image/jpeg"
        with open(image_path, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
        return f"data:{mime_type};base64,{encoded_string}"

    @property
    @abstractmethod
    def name(self) -> str:
        """提供者名称"""
        pass

    @property
    @abstractmethod
    def supports_vision(self) -> bool:
        """是否支持视觉能力"""
        pass

    def _get_mock_chat_response(self, messages: list[dict]) -> str:
        """获取文本对话的 Mock 响应"""
        is_reasoning = False
        for m in messages:
            content = m.get("content", "")
            if "iceberg_analysis" in content.lower() or "冰山" in content:
                is_reasoning = True
                break
                
        # 定义初始方案
        plan_1 = {
            "plan_id": "plan_1",
            "name": "粉色之梦 — 花果甜香",
            "category": "花果香调",
            "top_notes": [
                {"name": "佛手柑", "description": "明亮清新的开场", "reason": "呼应粉色系审美中的活力感"},
                {"name": "粉红胡椒", "description": "微辣的甜蜜点缀", "reason": "匹配甜美系风格中的俏皮元素"}
            ],
            "middle_notes": [
                {"name": "鸢尾花", "description": "粉质的优雅花香", "reason": "连接古典系审美与小众偏好"},
                {"name": "玫瑰", "description": "经典的浪漫花香", "reason": "呼应约会社交场景"}
            ],
            "base_notes": [
                {"name": "白檀", "description": "温柔的木质收尾", "reason": "提供温暖收尾"},
                {"name": "香草", "description": "甜蜜的温暖基调", "reason": "满足情绪需求"}
            ],
            "recommendation_reason": "这个方案直接呼应了目标群体的甜美系穿搭偏好和粉色系色彩倾向。",
            "fragrance_story": "她在镜子前最后确认了蝴蝶结的位置...",
            "iceberg_analysis": {
                "surface": "显性行为层分析...",
                "middle": "情感价值层分析...",
                "deep": "深层需求分析..."
            }
        }
        
        plan_2 = {
            "plan_id": "plan_2",
            "name": "暖阳之光 — 柑橘木质",
            "category": "柑橘木质调",
            "top_notes": [
                {"name": "甜橙", "description": "温暖明亮的柑橘香", "reason": "带来明快情绪"},
                {"name": "柠檬", "description": "酸甜活泼", "reason": "增加清新度"}
            ],
            "middle_notes": [
                {"name": "橙花", "description": "干净的白色花香", "reason": "提供洁净感"}
            ],
            "base_notes": [
                {"name": "雪松", "description": "干燥的木质香气", "reason": "提供沉静支撑"}
            ],
            "recommendation_reason": "暖阳之光提供温暖舒适的氛围，适合日常通勤使用。",
            "fragrance_story": "早晨第一缕阳光洒进房间...",
            "iceberg_analysis": {
                "surface": "表面行为...",
                "middle": "情感价值...",
                "deep": "深层需求..."
            }
        }
        
        plan_3 = {
            "plan_id": "plan_3",
            "name": "静谧之林 — 绿意苔藓",
            "category": "绿意苔藓调",
            "top_notes": [
                {"name": "薄荷", "description": "清凉提神", "reason": "瞬间抓耳"},
                {"name": "绿叶", "description": "青草气息", "reason": "贴近自然"}
            ],
            "middle_notes": [
                {"name": "茉莉", "description": "清幽茶香", "reason": "平复心境"}
            ],
            "base_notes": [
                {"name": "橡木苔", "description": "潮湿的泥土气息", "reason": "深邃静谧"}
            ],
            "recommendation_reason": "静谧之林带给调香师自然雨后的宁静，呼应独处与沉静渴望。",
            "fragrance_story": "漫步在雨后的森林中...",
            "iceberg_analysis": {
                "surface": "表面行为...",
                "middle": "情感价值...",
                "deep": "深层需求..."
            }
        }
        
        if is_reasoning:
            res = {
                "iceberg_analysis": {
                    "surface": "目标群体以年轻女性为主，偏好甜美与古典穿搭风格。",
                    "middle": "消费动机主要受情绪需求 and 社交场景驱动。", # 原句是: "消费动机主要受情绪需求和社交场景驱动。"
                    "deep": "深层对独特性和群体归属感有强烈的自我表达诉求。"
                },
                "recommendations": [plan_1, plan_2, plan_3]
            }
            # 修正原句中的 and 为 和 (跟 view_file 结果一致)
            res["iceberg_analysis"]["middle"] = "消费动机主要受情绪需求和社交场景驱动。"
            return json.dumps(res, ensure_ascii=False)
        
        # 否则是对话微调阶段
        last_user_msg = ""
        for m in reversed(messages):
            if m.get("role") == "user":
                last_user_msg = m.get("content", "")
                break
                
        # 检测微调关键字并合并变更
        updated_plans = []
        has_change = False
        
        # 我们用一个临时方案存储修改，使微调能够累积
        p1 = json.loads(json.dumps(plan_1))
        
        # 1. 沉香/乌木/woody
        if any(k in last_user_msg.lower() for k in ["woody", "沉香", "乌木"]):
            has_change = True
            p1["name"] = "暗夜玫瑰 — 花香木质"
            p1["category"] = "花香木质调"
            p1["base_notes"] = [
                {"name": "沉香", "description": "深沉的东方木质", "reason": "增加神秘感和深度，呼应哥特系偏好", "changed": True},
                {"name": "乌木", "description": "烟熏的暗色木质", "reason": "与粉色系形成「甜美×暗黑」的反差张力", "changed": True}
            ]
            p1["recommendation_reason"] = "修改后的方案保留了花果甜美的前中调，但通过沉香和乌木的后调创造了一个戏剧性的反转..."
            
        # 2. 葡萄柚/grapefruit
        if any(k in last_user_msg.lower() for k in ["grapefruit", "葡萄柚"]):
            has_change = True
            p1["top_notes"] = [
                {"name": "葡萄柚", "description": "酸甜清爽的柑橘前调", "reason": "增加前调的果香清爽度", "changed": True},
                {"name": "粉红胡椒", "description": "微辣的甜蜜点缀", "reason": "匹配甜美系风格中的俏皮元素"}
            ]
                
        # 3. 情绪/emotional
        if any(k in last_user_msg.lower() for k in ["emotional", "情绪"]):
            has_change = True
            p1["middle_notes"] = [
                {"name": "薰衣草", "description": "舒缓情绪的草本花香", "reason": "释放柠檬烯等成分，激活多巴胺，提供独特的情绪价值与疗愈", "changed": True},
                {"name": "玫瑰", "description": "经典的浪漫花香", "reason": "呼应约会社交场景"}
            ]
                
        # 4. 雪松/cedarwood
        if any(k in last_user_msg.lower() for k in ["cedarwood", "雪松"]):
            has_change = True
            p1["base_notes"] = [
                {"name": "雪松", "description": "干燥温暖的木质后调", "reason": "带来深沉干练的雪松意境", "changed": True},
                {"name": "香草", "description": "甜蜜的温暖基调", "reason": "满足情绪需求"}
            ]

        if has_change:
            updated_plans.append(p1)
            chat_data = {
                "updated_plans": updated_plans
            }
            return f"好的，我已经根据您的要求对配方进行了微调：\n\n```json\n{json.dumps(chat_data, ensure_ascii=False, indent=2)}\n```"
        else:
            return "收到您的反馈。这是一个关于该香氛配方建议的回答。如果您有具体的修改意见，比如更换某种前调或后调香材（如：沉香、葡萄柚、雪松等），请告诉我。"

    def _get_mock_vision_response(self, image_paths: list[str], prompt: str) -> str:
        """获取视觉分析的 Mock 响应"""
        if len(image_paths) > 1 and not any(k in prompt.lower() for k in ["grid", "网格", "组图"]):
            multi_results = [
                {
                    "穿搭风格": "优雅法式风格",
                    "人物/主题": "都市女性",
                    "消费水平": "中高"
                },
                {
                    "穿搭风格": "复古港风",
                    "人物/主题": "文艺青年",
                    "消费水平": "中高"
                }
            ]
            return json.dumps(multi_results, ensure_ascii=False)

        if "组图" in prompt or "网格" in prompt or "grid" in prompt:
            grid_results = [
                {
                    "grid_index": i + 1,
                    "wear": f"用户 {i+1} 穿搭风格",
                    "consumption_level": "中",
                    "style": "日常休闲"
                } for i in range(10)
            ]
            return json.dumps(grid_results, ensure_ascii=False)
        elif "视频" in prompt or "frame" in prompt:
            frame_result = {
                "wear": "运动外套配运动短裤",
                "wear_change": "从室内运动装切换为户外跑步装",
                "consumption_level": "中"
            }
            return json.dumps(frame_result, ensure_ascii=False)
        else:
            cover_result = {
                "穿搭单品": "粉色甜美连衣裙配小白鞋，精致配饰",
                "搜索关键词": ["甜美风", "约会穿搭", "粉色系"],
                "scene": "阳光花园下午茶",
                "消费水平": "中高",
                "生活方式/审美倾向": "追求精致仪式感与社交分享的生活态度"
            }
            return json.dumps(cover_result, ensure_ascii=False)
