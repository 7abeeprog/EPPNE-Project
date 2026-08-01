# app/core/logging_conf.py
import logging
import sys
import os
import contextvars
from typing import Optional
from app.core.config import settings

# ============================================================
# 🔥 السياق المتغير لتخزين Trace-ID عبر الطلبات (Async-Safe)
# ============================================================
_trace_id_var: contextvars.ContextVar[str] = contextvars.ContextVar(
    "trace_id", default="-"
)


def set_trace_id(trace_id: str) -> None:
    """تعيين Trace-ID للطلب الحالي."""
    _trace_id_var.set(trace_id)


def get_trace_id() -> str:
    """جلب Trace-ID للطلب الحالي."""
    return _trace_id_var.get()


# ============================================================
# 🔥 السياق المتغير لتخزين Sector (قطاع المستخدم)
# ============================================================
_sector_var: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "sector", default=None
)


def set_sector(sector: Optional[str]) -> None:
    """تعيين قطاع المستخدم الحالي في سياق الطلب."""
    _sector_var.set(sector)


def get_sector() -> Optional[str]:
    """جلب قطاع المستخدم الحالي من سياق الطلب."""
    return _sector_var.get()


# ============================================================
# 🔥 Filter مخصص لإضافة Trace-ID إلى كل سجل
# ============================================================
class TraceIDFilter(logging.Filter):
    """يُضيف trace_id إلى سجل اللوغات (Log Record) تلقائياً."""
    def filter(self, record: logging.LogRecord) -> bool:
        record.trace_id = get_trace_id()
        return True


# ============================================================
# إعداد نظام التسجيل الأساسي (Production-Ready)
# ============================================================
def setup_logging() -> None:
    """تهيئة نظام التسجيل مع دعم Trace-ID وإعدادات البيئة."""
    # 1. التأكد من وجود مجلد السجلات
    if settings.LOG_FILE:
        log_dir = os.path.dirname(settings.LOG_FILE)
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)

    # 2. قراءة مستوى التسجيل بأمان
    try:
        log_level_name = settings.LOG_LEVEL.upper()
    except AttributeError:
        log_level_name = "INFO"
        print(
            f"⚠️ [CRITICAL WAKE-UP] LOG_LEVEL missing in Settings! Defaulting to INFO. Please check config.py",
            file=sys.stderr
        )

    log_level = getattr(logging, log_level_name, logging.INFO)

    # 3. تنسيق السجل المتقدم (يتضمن Trace-ID)
    log_format = "%(asctime)s [%(levelname)s] [%(trace_id)s] %(name)s: %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"

    # 4. إنشاء المعالجات (Handlers)
    handlers = [
        logging.StreamHandler(sys.stdout),
    ]

    if settings.LOG_FILE:
        file_handler = logging.FileHandler(settings.LOG_FILE, encoding="utf-8")
        handlers.append(file_handler)

    # 5. تكوين التنسيق الأساسي
    logging.basicConfig(
        level=log_level,
        format=log_format,
        datefmt=date_format,
        handlers=handlers,
    )

    # 6. تطبيق TraceIDFilter على جميع المعالجات
    root_logger = logging.getLogger()
    trace_filter = TraceIDFilter()
    for handler in root_logger.handlers:
        handler.addFilter(trace_filter)

    # 7. تهدئة الضجيج في الإنتاج
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)

    # 8. تأكيد بدء التشغيل
    logger = logging.getLogger("eppne")
    logger.info(f"✅ Logging system initialized with Trace-ID support. Level: {log_level_name}")


# ============================================================
# الـ Logger العام للمشروع
# ============================================================
logger = logging.getLogger("eppne")