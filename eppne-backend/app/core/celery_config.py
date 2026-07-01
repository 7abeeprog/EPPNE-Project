# app/core/celery_config.py
"""
تكوين Celery مع تحديد أولويات الطوابير
"""
from celery.schedules import crontab
from kombu import Queue, Exchange

# ========== طوابير Celery حسب القطاع ==========
task_queues = (
    Queue("default", Exchange("default"), routing_key="default"),
    Queue("saas", Exchange("saas"), routing_key="saas"),
    Queue("academy", Exchange("academy"), routing_key="academy"),
    Queue("commerce", Exchange("commerce"), routing_key="commerce"),
    Queue("affiliate", Exchange("affiliate"), routing_key="affiliate"),
    # ========== طوابير Agritech (مع الأولويات) ==========
    Queue("agritech.high", Exchange("agritech.high"), routing_key="agritech.high"),
    Queue("agritech.medium", Exchange("agritech.medium"), routing_key="agritech.medium"),
    Queue("agritech.low", Exchange("agritech.low"), routing_key="agritech.low"),
)

# ========== توجيه المهام إلى الطوابير المناسبة ==========
task_routes = {
    "saas.*": {"queue": "saas"},
    "academy.*": {"queue": "academy"},
    "commerce.*": {"queue": "commerce"},
    "affiliate.*": {"queue": "affiliate"},
    # Agritech - سيتم تحديد الطابور ديناميكياً في الكود
    "agritech.*": {"queue": "agritech.high"},  # القيمة الافتراضية
}

# ========== عدد المهام المتزامنة لكل طابور ==========
task_concurrency = {
    'agritech.high': 10,
    'agritech.medium': 5,
    'agritech.low': 2,
}

# ========== جدولة المهام المتكررة (Beat) ==========
beat_schedule = {
    "process-auto-renewals": {
        "task": "saas.process_auto_renewals",
        "schedule": crontab(hour=2, minute=0),  # 2:00 AM يومياً
        "options": {"queue": "saas"},
    },
    "generate-monthly-invoices": {
        "task": "saas.generate_monthly_invoices",
        "schedule": crontab(day_of_month=1, hour=3, minute=0),  # أول كل شهر
        "options": {"queue": "saas"},
    },
    "check-expired-trials": {
        "task": "saas.check_expired_trials",
        "schedule": crontab(hour=4, minute=0),  # 4:00 AM يومياً
        "options": {"queue": "saas"},
    },
    # ========== مهام Agritech المتكررة ==========
    "process-soil-readings": {
        "task": "agritech.process_soil_readings",
        "schedule": crontab(minute="*/15"),  # كل 15 دقيقة
        "options": {"queue": "agritech.high"},
    },
    "generate-agricultural-reports": {
        "task": "agritech.generate_reports",
        "schedule": crontab(hour=6, minute=0),  # 6:00 AM يومياً
        "options": {"queue": "agritech.medium"},
    },
    "cleanup-expired-qrs": {
        "task": "agritech.cleanup_expired_qrs",
        "schedule": crontab(hour=1, minute=0),  # 1:00 AM يومياً
        "options": {"queue": "agritech.low"},
    },
}