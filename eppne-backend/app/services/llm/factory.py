# app/services/llm/factory.py
from .gemini_adapter import GeminiAdapter
from .openai_adapter import OpenAIAdapter
from .claude_adapter import ClaudeAdapter
from .kimi_adapter import KimiAdapter  # 🔥 جديد

class LLMFactory:
    @staticmethod
    def get_llm(model_name: str) -> BaseLLMAdapter:
        if "gemini" in model_name.lower():
            return GeminiAdapter(model_name)
        elif "gpt" in model_name.lower():
            return OpenAIAdapter(model_name)
        elif "claude" in model_name.lower():
            return ClaudeAdapter(model_name)
        elif "kimi" in model_name.lower():
            return KimiAdapter(model_name)  # 🔥 جديد
        else:
            raise ValueError(f"Unsupported model: {model_name}")