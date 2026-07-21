# app/core/metrics.py
"""
مراقبة الأداء وجمع المقاييس (Metrics)
"""

import time
from typing import Dict, List
from collections import defaultdict
from datetime import datetime, timedelta

class MetricsCollector:
    """جمع مقاييس الأداء للطلبات والاستعلامات"""
    
    _instance = None
    _metrics: Dict[str, List[float]] = defaultdict(list)
    _max_samples = 1000  # الحد الأقصى للعينات
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def record_request(self, path: str, method: str, duration: float):
        """تسجيل زمن استجابة طلب"""
        key = f"{method}:{path}"
        self._metrics[key].append(duration)
        if len(self._metrics[key]) > self._max_samples:
            self._metrics[key] = self._metrics[key][-self._max_samples:]
    
    def record_query(self, query_name: str, duration: float):
        """تسجيل زمن استعلام قاعدة البيانات"""
        key = f"query:{query_name}"
        self._metrics[key].append(duration)
        if len(self._metrics[key]) > self._max_samples:
            self._metrics[key] = self._metrics[key][-self._max_samples:]
    
    def get_stats(self, key: str) -> dict:
        """الحصول على إحصائيات لمفتاح معين"""
        values = self._metrics.get(key, [])
        if not values:
            return {"count": 0, "avg": 0, "max": 0, "min": 0, "p95": 0}
        
        sorted_values = sorted(values)
        return {
            "count": len(values),
            "avg": sum(values) / len(values),
            "max": max(values),
            "min": min(values),
            "p95": sorted_values[int(len(values) * 0.95)] if len(values) > 1 else values[0],
        }
    
    def get_all_stats(self) -> dict:
        """الحصول على جميع الإحصائيات"""
        return {key: self.get_stats(key) for key in self._metrics.keys()}

metrics = MetricsCollector()