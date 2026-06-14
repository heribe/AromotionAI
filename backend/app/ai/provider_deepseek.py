import os
import httpx
from .base import AIProvider

class DeepSeekProvider(AIProvider):
    """DeepSeek AI Provider Implementation"""

    def __init__(self, api_key: str = None, base_url: str = None):
        self._api_key = api_key or os.getenv("DEEPSEEK_API_KEY")
        self._base_url = base_url or os.getenv("DEEPSEEK_BASE_URL") or "https://api.deepseek.com/"

    @property
    def name(self) -> str:
        return "deepseek"

    @property
    def supports_vision(self) -> bool:
        return False

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
            "model": kwargs.get("model", "deepseek-chat"),
            "messages": messages,
            **{k: v for k, v in kwargs.items() if k != "model"}
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]

    async def vision(self, image_paths: list[str], prompt: str, **kwargs) -> str:
        raise NotImplementedError("DeepSeek API does not support vision capability.")
