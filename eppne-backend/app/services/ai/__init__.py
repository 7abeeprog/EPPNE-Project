# app/services/ai/__init__.py
"""
حزمة الذكاء الاصطناعي - المزيج الرباعي
"""

from app.services.ai.engine import AIEngine, ai_engine
from app.services.ai.models import (
    AIModelId,
    ModelConfig,
    MODEL_CONFIGS,
    TaskType,
    ModelTier,
    DEFAULT_ROUTING_PERCENTAGES,
)
from app.services.ai.router import AIRouter
from app.services.ai.cache import SemanticCache, PromptCache, BatchProcessor
from app.services.ai.cost_tracker import CostTracker

__all__ = [
    "AIEngine",
    "ai_engine",
    "AIModelId",
    "ModelConfig",
    "MODEL_CONFIGS",
    "TaskType",
    "ModelTier",
    "DEFAULT_ROUTING_PERCENTAGES",
    "AIRouter",
    "SemanticCache",
    "PromptCache",
    "BatchProcessor",
    "CostTracker",
]