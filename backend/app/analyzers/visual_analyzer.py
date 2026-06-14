import os
import logging
from app.analyzers.base import BaseAnalyzer

logger = logging.getLogger(__name__)

class VisualAnalyzer(BaseAnalyzer):
    """视觉分析器，负责分析封面、视频帧和网格图片"""

    async def analyze_cover(self, image_path: str) -> dict:
        """
        分析小红书/抖音封面图
        
        Args:
            image_path: 封面图片本地路径
            
        Returns:
            dict: 包含穿搭单品、搜索关键词、场景城市线索、消费水平、生活方式与审美倾向的分析结果
        """
        provider, model_name = self._get_provider_for_slot("visual_analysis")

        prompt = (
            "请分析这张时尚封面图片，并以 JSON 格式输出以下字段（不要包含任何 Markdown 以外的说明文字，直接返回 JSON 代码块）：\n"
            "{\n"
            '  "穿搭单品": "描述画面中人物穿着的品类、颜色、材质或品牌线索",\n'
            '  "搜索关键词": ["关键词1", "关键词2", "关键词3"],\n'
            '  "scene": "分析画面中呈现的场景与城市线索，例如：下午茶、街拍、约会、一线城市等",\n'
            '  "场景和城市线索": "同上，用于兼容旧契约的字段描述",\n'
            '  "消费水平": "估算该用户的消费水平，可选值包括：低、中、中高、高",\n'
            '  "生活方式/审美倾向": "描述该用户所表达的生活方式、社交态度与审美倾向"\n'
            "}"
        )

        fallback = {
            "穿搭单品": "",
            "搜索关键词": [],
            "scene": "",
            "场景和城市线索": "",
            "消费水平": "中",
            "生活方式/审美倾向": ""
        }

        try:
            raw_res = await provider.vision(
                image_paths=[image_path],
                prompt=prompt,
                model=model_name
            )
            result = self.parse_json_safely(raw_res, fallback)
            
            # 确保契约闭环：填充缺失字段，且把 "场景和城市线索" 与 "scene" 做同步
            if isinstance(result, dict):
                for k, v in fallback.items():
                    if k not in result:
                        result[k] = v
                # 同步 scene 和 场景和城市线索
                if result.get("scene") and not result.get("场景和城市线索"):
                    result["场景和城市线索"] = result["scene"]
                elif result.get("场景和城市线索") and not result.get("scene"):
                    result["scene"] = result["场景和城市线索"]
                return result
            return fallback

        except Exception as e:
            logger.error(f"Error in analyze_cover for {image_path}: {e}", exc_info=True)
            return fallback

    async def analyze_video_frame(self, frame_path: str) -> dict:
        """
        分析视频帧图片
        
        Args:
            frame_path: 视频帧图片本地路径
            
        Returns:
            dict: 包含穿搭单品、搭配变化、消费水平的分析结果
        """
        provider, model_name = self._get_provider_for_slot("visual_analysis")

        prompt = (
            "请简洁分析该视频帧图片，并以 JSON 格式输出以下字段（只返回 JSON，不要包含任何说明文字）：\n"
            "{\n"
            '  "wear": "主要穿搭单品说明（品类、风格等）",\n'
            '  "wear_change": "分析视频中的搭配变化（若无明显变化，写明无明显变化或为空）",\n'
            '  "consumption_level": "估算的消费水平，可选值：低、中、中高、高"\n'
            "}"
        )

        fallback = {
            "wear": "",
            "wear_change": "",
            "consumption_level": "中"
        }

        try:
            raw_res = await provider.vision(
                image_paths=[frame_path],
                prompt=prompt,
                model=model_name
            )
            result = self.parse_json_safely(raw_res, fallback)

            if isinstance(result, dict):
                # 确保契约闭环：填充缺失字段
                for k, v in fallback.items():
                    if k not in result:
                        result[k] = v
                return result
            return fallback

        except Exception as e:
            logger.error(f"Error in analyze_video_frame for {frame_path}: {e}", exc_info=True)
            return fallback

    async def analyze_grid(self, grid_path: str, person_count: int) -> list[dict]:
        """
        分析 2x5 网格组图（最多10格封面）
        
        Args:
            grid_path: 网格图片本地路径
            person_count: 网格中有效用户的数量（通常为 1~10）
            
        Returns:
            list[dict]: 每一格封面的分析结果列表
        """
        provider, model_name = self._get_provider_for_slot("visual_analysis")

        prompt = (
            f"输入图片是一个由多张封面拼接成的 2x5 网格图（从左到右，从上到下）。\n"
            f"请逐格分析前 {person_count} 个格子的信息（每一格代表一个不同用户的封面），\n"
            f"并输出一个 JSON 数组，数组长度需精确为 {person_count}，不要返回任何说明文字。\n"
            f"JSON 数组中每个对象的格式必须为：\n"
            "{\n"
            '  "grid_index": 1, // 格子的序号（从1到10）\n'
            '  "wear": "穿搭单品/人物类型/主题分析",\n'
            '  "consumption_level": "估算的消费水平，可选值：低、中、中高、高",\n'
            '  "style": "该封面所呈现的审美风格或穿搭流派"\n'
            "}"
        )

        fallback = [
            {
                "grid_index": i + 1,
                "wear": "",
                "consumption_level": "中",
                "style": ""
            } for i in range(person_count)
        ]

        try:
            raw_res = await provider.vision(
                image_paths=[grid_path],
                prompt=prompt,
                model=model_name
            )
            result = self.parse_json_safely(raw_res, fallback)

            if isinstance(result, list):
                # 确保数组长度正确且格式闭环
                validated_results = []
                for i in range(person_count):
                    # 如果返回的数组元素不足，用 fallback 补齐
                    if i < len(result) and isinstance(result[i], dict):
                        item = result[i]
                        # 补齐缺少的 key
                        for k, v in fallback[i].items():
                            if k not in item:
                                item[k] = v
                        validated_results.append(item)
                    else:
                        validated_results.append(fallback[i])
                return validated_results
            return fallback

        except Exception as e:
            logger.error(f"Error in analyze_grid for {grid_path}: {e}", exc_info=True)
            return fallback
