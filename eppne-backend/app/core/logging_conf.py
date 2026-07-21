# app/core/logging_conf.py
import logging
import sys
import os
from app.core.config import settings

def setup_logging():
    # التحقق من صحة مسار ملف السجل
    if settings.LOG_FILE:
        log_dir = os.path.dirname(settings.LOG_FILE)
        if log_dir:  # تجنب محاولة إنشاء دليل فارغ
            os.makedirs(log_dir, exist_ok=True)

    # استراتيجية الخبير: التعامل الآمن مع المتغير مع تنبيه واضح
    try:
        log_level_name = settings.LOG_LEVEL.upper()
    except AttributeError:
        # هذا السيناريو لن يحدث بعد تعديل config.py، لكن وضعه احترازي لإنقاذ السيرفر
        log_level_name = "INFO"
        print(f"⚠️ [CRITICAL WAKE-UP] LOG_LEVEL missing in Settings! Defaulting to INFO. Please check config.py", file=sys.stderr)

    logging.basicConfig(
        level=getattr(logging, log_level_name, logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(settings.LOG_FILE) if settings.LOG_FILE else logging.NullHandler()
        ]
    )
    
    # تهدئة ضجيج SQLAlchemy في الإنتاج
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    
    # سجل بدء التشغيل للتأكيد
    logger = logging.getLogger("eppne")
    logger.info(f"✅ Logging system initialized successfully with level: {log_level_name}")

# هذا هو الـ Logger العام للمشروع
logger = logging.getLogger("eppne")