import os
import httpx
from .base import AIProvider

class OpenAIProvider(AIProvider):
    """OpenAI AI Provider Implementation"""

    def __init__(self, api_key: str = None, base_url: str = None):
        self._api_key = api_key or os.getenv("OPENAI_API_KEY")
        self._base_url = base_url or os.getenv("OPENAI_BASE_URL") or "https://api.openai.com/v1/"

    @property
    def name(self) -> str:
        return "openai"

    @property
    def supports_vision(self) -> bool:
        return True

    def _is_mock_mode(self) -> bool:
        return os.getenv("AROMOTION_TEST_MODE") == "mock" or not self._api_key

    async def chat(self, messages: list[dict], **kwargs) -> str:
        if self._is_mock_mode():
            return self._get_mock_chat_response(messages)

        base_url_str = self._base_url
        if not base_url_str.endswith("/"):
            base_url_str += "/"
        url = base_url_str + "chat/completions"

        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": kwargs.get("model", "gpt-4o"),
            "messages": messages,
            **{k: v for k, v in kwargs.items() if k != "model"}
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]

    async def vision(self, image_paths: list[str], prompt: str, **kwargs) -> str:
        if self._is_mock_mode():
            return self._get_mock_vision_response(image_paths, prompt)

        base_url_str = self._base_url
        if not base_url_str.endswith("/"):
            base_url_str += "/"
        url = base_url_str + "chat/completions"

        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json"
        }

        # 视觉 vision() 将本地图片 Base64 编码后组装为 Data URI 发送
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
            "model": kwargs.get("model", "gpt-4o"),
            "messages": messages,
            **{k: v for k, v in kwargs.items() if k != "model"}
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]
