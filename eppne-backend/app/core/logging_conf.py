# app/core/logging_conf.py
import logging
import sys
import os
from app.core.config import settings

def setup_logging():
    if settings.LOG_FILE:
        os.makedirs(os.path.dirname(settings.LOG_FILE), exist_ok=True)

    logging.basicConfig(
        level=getattr(logging, settings.LOG_LEVEL),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(settings.LOG_FILE) if settings.LOG_FILE else logging.NullHandler()
        ]
    )
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

# 🔥 هذا هو السطر الذي كان ينقصك في المستوى الأعلى للملف
logger = logging.getLogger("eppne")