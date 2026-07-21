# app/services/ai/cost_tracker.py
"""
نظام تتبع التكلفة لكل نموذج وبكل عملية
"""

import json
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

from app.core.redis_client import redis_client
from app.services.ai.models import ModelConfig, AIModelId, MODEL_CONFIGS


class CostTracker:
    """
    تتبع تكلفة استخدام كل نموذج
    يخزن الإحصائيات في Redis مع صلاحية 30 يوم
    """

    PREFIX = "ai:cost:"
    DAILY_PREFIX = "ai:cost:daily:"
    MONTHLY_PREFIX = "ai:cost:monthly:"

    @classmethod
    def _get_key(cls, model_id: str, period: str = "total") -> str:
        """توليد مفتاح التخزين"""
        return f"{cls.PREFIX}{model_id}:{period}"

    @classmethod
    async def record_usage(cls, model_id: str, input_tokens: int, output_tokens: int) -> Dict[str, float]:
        """
        تسجيل استخدام نموذج وحساب التكلفة
        يعيد التكلفة المحسوبة
        """
        config = MODEL_CONFIGS.get(AIModelId(model_id))
        if not config:
            return {"cost": 0.0, "input_cost": 0.0, "output_cost": 0.0}

        # حساب التكلفة
        input_cost = (input_tokens / 1_000_000) * config.input_cost_per_1m
        output_cost = (output_tokens / 1_000_000) * config.output_cost_per_1m
        total_cost = input_cost + output_cost

        # تسجيل في Redis (إجمالي + يومي + شهري)
        today = datetime.utcnow().strftime("%Y-%m-%d")
        month = datetime.utcnow().strftime("%Y-%m")

        # تجميع البيانات
        usage_data = {
            "model_id": model_id,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "input_cost": input_cost,
            "output_cost": output_cost,
            "total_cost": total_cost,
            "timestamp": datetime.utcnow().isoformat()
        }

        # تخزين في Redis مع زيادة العداد
        total_key = cls._get_key(model_id, "total")
        daily_key = f"{cls.DAILY_PREFIX}{model_id}:{today}"
        monthly_key = f"{cls.MONTHLY_PREFIX}{model_id}:{month}"

        # استخدام Hash لتخزين المجاميع
        await redis_client.hincrbyfloat(total_key, "input_tokens", input_tokens)
        await redis_client.hincrbyfloat(total_key, "output_tokens", output_tokens)
        await redis_client.hincrbyfloat(total_key, "total_cost", total_cost)
        await redis_client.expire(total_key, 60 * 60 * 24 * 30)  # 30 يوم

        await redis_client.hincrbyfloat(daily_key, "input_tokens", input_tokens)
        await redis_client.hincrbyfloat(daily_key, "output_tokens", output_tokens)
        await redis_client.hincrbyfloat(daily_key, "total_cost", total_cost)
        await redis_client.expire(daily_key, 60 * 60 * 24 * 2)  # يومين

        await redis_client.hincrbyfloat(monthly_key, "input_tokens", input_tokens)
        await redis_client.hincrbyfloat(monthly_key, "output_tokens", output_tokens)
        await redis_client.hincrbyfloat(monthly_key, "total_cost", total_cost)
        await redis_client.expire(monthly_key, 60 * 60 * 24 * 60)  # 60 يوم

        return {
            "cost": total_cost,
            "input_cost": input_cost,
            "output_cost": output_cost,
        }

    @classmethod
    async def get_total_cost(cls, model_id: Optional[str] = None) -> Dict[str, float]:
        """جلب إجمالي التكلفة لنموذج معين أو لجميع النماذج"""
        if model_id:
            key = cls._get_key(model_id, "total")
            data = await redis_client.hgetall(key)
            return {
                "input_tokens": float(data.get("input_tokens", 0)),
                "output_tokens": float(data.get("output_tokens", 0)),
                "total_cost": float(data.get("total_cost", 0)),
            }
        else:
            # حساب تكلفة جميع النماذج
            total = {"input_tokens": 0, "output_tokens": 0, "total_cost": 0}
            for model in AIModelId:
                cost = await cls.get_total_cost(model.value)
                total["input_tokens"] += cost["input_tokens"]
                total["output_tokens"] += cost["output_tokens"]
                total["total_cost"] += cost["total_cost"]
            return total

    @classmethod
    async def get_daily_cost(cls, model_id: str, date: Optional[str] = None) -> Dict[str, float]:
        """جلب تكلفة يوم معين"""
        if not date:
            date = datetime.utcnow().strftime("%Y-%m-%d")
        key = f"{cls.DAILY_PREFIX}{model_id}:{date}"
        data = await redis_client.hgetall(key)
        return {
            "input_tokens": float(data.get("input_tokens", 0)),
            "output_tokens": float(data.get("output_tokens", 0)),
            "total_cost": float(data.get("total_cost", 0)),
        }

    @classmethod
    async def get_monthly_cost(cls, model_id: str, month: Optional[str] = None) -> Dict[str, float]:
        """جلب تكلفة شهر معين"""
        if not month:
            month = datetime.utcnow().strftime("%Y-%m")
        key = f"{cls.MONTHLY_PREFIX}{model_id}:{month}"
        data = await redis_client.hgetall(key)
        return {
            "input_tokens": float(data.get("input_tokens", 0)),
            "output_tokens": float(data.get("output_tokens", 0)),
            "total_cost": float(data.get("total_cost", 0)),
        }