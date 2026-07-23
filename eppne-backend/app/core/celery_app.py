# app/core/celery_app.py
"""
تطبيق Celery المركزي للمنصة السيادية EPPNE.
يدير جميع المهام غير المتزامنة عبر Redis، مع دعم إعادة المحاولة،
حدود زمنية، وتوزيع تلقائي للمهام عبر القطاعات.
"""
from celery import Celery, shared_task
from app.core.config import settings
import os

# ============================================================
# 1. تهيئة تطبيق Celery الأساسي
# ============================================================
celery_app = Celery(
    "eppne_worker",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

# ============================================================
# 2. تحميل التكوين المتقدم من celery_config.py
# ============================================================
celery_app.config_from_object('app.core.celery_config', namespace='CELERY')

# ============================================================
# 3. الاكتشاف التلقائي للمهام (Auto-discovery)
# ============================================================
celery_app.autodiscover_tasks([
    'app.tasks',                     # يكتشف: affiliate, agritech, billing, commerce, deployment, employment, governance, saas_tasks
    'app.domains',                   # 🔥 يكتشف: privacy.tasks, وأي tasks.py مستقبلية في أي قطاع
], related_name='tasks', force=True)

# ============================================================
# 4. تحديثات التكوين النهائية (تجاوز لضمان الأمان والأداء)
# ============================================================
celery_app.conf.update(
    # ------ التسلسل والوقت ------
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    
    # ------ استراتيجية التنفيذ (لمنع فقدان المهام) ------
    task_acks_late=True,                # 🔥 تأكيد المهمة بعد التنفيذ (ليست قبلها)
    worker_prefetch_multiplier=1,       # 🔥 يمنع تجميع المهام (مثالي للعمليات الطويلة)
    task_reject_on_worker_lost=True,    # يرفض المهمة إذا تعطل الـ Worker ليعيد جدولتها
    
    # ------ الحدود الزمنية للحماية من المهام المعلقة (Hanging Tasks) ------
    task_time_limit=3600,               # الحد الأقصى الكلي: ساعة واحدة (60 دقيقة)
    task_soft_time_limit=3000,          # الإنذار المبكر: 50 دقيقة (للتسجيل قبل القتل)
    
    # ------ المراقبة والتحليلات ------
    task_track_started=True,            # يظهر في Flower متى بدأت المهمة
    task_send_sent_event=True,          # يرسل حدث عند إرسال المهمة (للمراقبة)
    
    # ------ إدارة النتائج ------
    result_expires=86400,               # نتائج المهام تنتهي بعد 24 ساعة (توفير الذاكرة)
    
    # ------ الاتصال ------
    broker_connection_retry_on_startup=True,  # يحاول إعادة الاتصال بـ Redis عند بدء التشغيل
)

# ============================================================
# 5. مهام وهمية (Fallback) لتجنب أخطاء الاستيراد في الكود القديم
# ============================================================
@shared_task(name="send_notification_task")
def send_notification_task(*args, **kwargs):
    """مهمة إرسال إشعار (مؤقتة - سيتم استبدالها بمهمة حقيقية لاحقاً)"""
    pass

@shared_task(name="send_email_task")
def send_email_task(*args, **kwargs):
    """مهمة إرسال بريد إلكتروني (مؤقتة - سيتم استبدالها بمهمة حقيقية لاحقاً)"""
    pass

# ============================================================
# 6. تحذير في حال لم يتم ضبط REDIS_URL
# ============================================================
if not settings.REDIS_URL:
    import warnings
    warnings.warn(
        "⚠️ REDIS_URL is not set in environment variables! "
        "Celery will fail to connect to the broker.",
        RuntimeWarning
    )