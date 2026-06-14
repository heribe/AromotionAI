import os
import json
import httpx
from .base import AIProvider

class GLMProvider(AIProvider):
    """GLM AI Provider Implementation"""

    def __init__(self, api_key: str = None, base_url: str = None):
        self._api_key = api_key or os.getenv("ZHIPUAI_API_KEY") or os.getenv("GLM_API_KEY")
        # 兼容兼容端点: https://open.bigmodel.cn/api/paas/v4/chat/completions
        # 基础 URL 通常为 https://open.bigmodel.cn/api/paas/v4/
        self._base_url = base_url or os.getenv("ZHIPUAI_BASE_URL") or "https://open.bigmodel.cn/api/paas/v4/"

    @property
    def name(self) -> str:
        return "glm"

    @property
    def supports_vision(self) -> bool:
        return True

    def _is_mock_mode(self) -> bool:
        return os.getenv("AROMOTION_TEST_MODE") == "mock" or not self._api_key

    async def _stream_completion(self, payload: dict) -> str:
        """流式调用 chat/completions，逐 chunk 累积 content 并返回完整文本。

        采用 stream=True 的核心动机：thinking 模型（如 glm-5.2）的推理 + 长生成
        总耗时可能远超固定 read timeout；流式下只要 chunk 持续流出连接即保持活跃，
        不会因"总时长"触发超时。reasoning_content 流式流出但不计入返回（业务只需 content）。
        """
        base_url_str = self._base_url
        if not base_url_str.endswith("/"):
            base_url_str += "/"
        url = base_url_str + "chat/completions"

        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        # 强制流式（不覆盖调用方可能误传的 stream=False）
        payload = {**payload, "stream": True}

        parts: list[str] = []
        async with httpx.AsyncClient(timeout=180.0) as client:
            async with client.stream("POST", url, headers=headers, json=payload) as response:
                # 流式下错误响应体仍需读取后再抛出，否则 raise_for_status 拿不到 body
                if response.status_code >= 400:
                    body = await response.aread()
                    response._raise_for_status(body)  # noqa: SLF001
                async for line in response.aiter_lines():
                    if not line or not line.startswith("data:"):
                        continue
                    data_str = line[5:].strip()
                    if data_str == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data_str)
                    except json.JSONDecodeError:
                        continue
                    choices = chunk.get("choices") or []
                    if not choices:
                        continue
                    delta = choices[0].get("delta") or {}
                    piece = delta.get("content")
                    if piece:
                        parts.append(piece)
        return "".join(parts)

    async def chat(self, messages: list[dict], **kwargs) -> str:
        if self._is_mock_mode():
            return self._get_mock_chat_response(messages)

        payload = {
            "model": kwargs.get("model", "glm-4"),
            "messages": messages,
            **{k: v for k, v in kwargs.items() if k != "model"},
        }
        return await self._stream_completion(payload)

    async def vision(self, image_paths: list[str], prompt: str, **kwargs) -> str:
        if self._is_mock_mode():
            return self._get_mock_vision_response(image_paths, prompt)

        # 构建 GLM v4 兼容的多模态内容格式
        content_list = [{"type": "text", "text": prompt}]
        for path in image_paths:
            data_uri = self._encode_image_to_data_uri(path)
            content_list.append({
                "type": "image_url",
                "image_url": {
                    "url": data_uri
                }
            })

        messages = [
            {
                "role": "user",
                "content": content_list
            }
        ]

        payload = {
            "model": kwargs.get("model", "glm-4v"),
            "messages": messages,
            **{k: v for k, v in kwargs.items() if k != "model"},
        }
        return await self._stream_completion(payload)
