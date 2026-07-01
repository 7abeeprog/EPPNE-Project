# app/services/llm/kimi_adapter.py
import httpx
import json
from app.core.config import settings
from .base import BaseLLMAdapter

class KimiAdapter(BaseLLMAdapter):
    def __init__(self, model_name: str = "kimi-k2.6"):
        self.model_name = model_name
        self.api_key = settings.KIMI_API_KEY
        self.base_url = settings.KIMI_BASE_URL or "https://api.moonshot.cn/v1"

    async def generate_response(self, system_prompt: str, user_prompt: str) -> str:
        """توليد رد من Kimi K2.6."""
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": self.model_name,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    "temperature": 0.7,
                    "max_tokens": 8192
                }
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]