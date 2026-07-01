# app/core/celery_app.py
from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "eppne_worker",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.domains.privacy.tasks"] # إدراج المهام تلقائياً
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True, # 🔥 ضمان عدم ضياع المهام في حال تعطل الـ Worker
    worker_prefetch_multiplier=1, # 🔥 مهم جداً للمهام طويلة الأمد
    task_reject_on_worker_lost=True,
)