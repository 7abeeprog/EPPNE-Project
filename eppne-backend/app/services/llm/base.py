# app/services/llm/base.py
from abc import ABC, abstractmethod

class BaseLLMAdapter(ABC):
    """الفئة الأساسية (Interface) لجميع محولات النماذج اللغوية (LLMs)"""
    pass
    
    # يمكنك إضافة الدوال الأساسية هنا لاحقاً مثل:
    # @abstractmethod
    # async def generate_text(self, prompt: str) -> str:
    #     pass