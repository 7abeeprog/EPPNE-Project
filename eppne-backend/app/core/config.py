# app/core/config.py
import os
from dotenv import load_dotenv
from pydantic_settings import BaseSettings
from pydantic import Field, ConfigDict, field_validator
from typing import Optional, List, Dict

# تحميل متغيرات البيئة من ملف .env (يجب أن يكون في جذر المشروع)
load_dotenv()

class Settings(BaseSettings):
    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False
    )

    # ========== قاعدة البيانات ==========
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://eppne:eppne123@localhost:5432/eppne",
        description="رابط اتصال PostgreSQL (AsyncPG)"
    )
    DATABASE_POOL_SIZE: int = Field(default=20, ge=1)
    DATABASE_MAX_OVERFLOW: int = Field(default=40, ge=0)

    # ========== Redis ==========
    REDIS_URL: str = Field(
        default="redis://localhost:6379/0",
        description="رابط اتصال Redis (للتخزين المؤقت و Idempotency)"
    )
    REDIS_PASSWORD: Optional[str] = Field(default=None, description="كلمة مرور Redis إن وجدت")
    REDIS_MAX_CONNECTIONS: int = Field(default=20, ge=5)

    # ========== JWT والمصادقة ==========
    SECRET_KEY: str = Field(default="CHANGE_ME_NOW", min_length=32, description="المفتاح السري لتوقيع التوكنات")
    ALGORITHM: str = Field(default="HS256", description="خوارزمية التشفير")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=10080, description="صلاحية توكن الوصول (7 أيام)")
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=30, description="صلاحية توكن التحديث (30 يوم)")

    # ========== المستخدم السوبر الأول ==========
    FIRST_SUPERUSER_EMAIL: str = Field(default="admin@eppne.com")
    FIRST_SUPERUSER_PASSWORD: str = Field(default="ChangeMe@123")
    FIRST_SUPERUSER_USERNAME: str = Field(default="sovereign_admin")
    FIRST_SUPERUSER_NAME_AR: str = Field(default="المدير التنفيذي")
    FIRST_SUPERUSER_NAME_EN: str = Field(default="Executive Director")

    # ========== العملات والصرافة ==========
    CRYPTO_MODE: str = Field(default="FULL_CRYPTO", description="FULL_CRYPTO أو POINTS_ONLY")
    EXCHANGE_RATES: Dict[str, float] = Field(
        default={
            "MR_POUND": 1.0,
            "MR_USDT": 50.0,
            "MR7": 5.0,
            "NBT": 250.0,
            "MRX": 500.0,
        },
        description="أسعار الصرف مقابل العملة الأساسية MR_POUND"
    )

    # ========== تخزين الملفات (MinIO / S3) ==========
    S3_ENDPOINT: str = Field(default="localhost:9000")
    S3_ACCESS_KEY: str = Field(default="minioadmin")
    S3_SECRET_KEY: str = Field(default="minioadmin")
    S3_BUCKET_MEDIA: str = Field(default="eppne-media")
    S3_BUCKET_CERTIFICATES: str = Field(default="eppne-certs")
    S3_USE_SSL: bool = Field(default=False)

    # ========== WebSocket ==========
    WS_HEARTBEAT_INTERVAL: int = Field(default=30, description="فترة نبض WebSocket بالثواني")

    # ========== تحديد المعدل (Rate Limiting) ==========
    RATE_LIMIT_PER_MINUTE: int = Field(default=60, description="الحد الأقصى للطلبات العادية في الدقيقة")
    RATE_LIMIT_PER_MINUTE_AUTH: int = Field(default=10, description="الحد الأقصى لطلبات المصادقة في الدقيقة")

    # ========== البلوكتشين (Web3) ==========
    BLOCKCHAIN_RPC_URL: Optional[str] = Field(default=None)
    CHAIN_ID: int = Field(default=1337)

    # ========== التسجيل (Logging) ==========
    LOG_LEVEL: str = Field(default="INFO", description="مستوى التسجيل (DEBUG, INFO, WARNING, ERROR)")
    LOG_FILE: Optional[str] = Field(default="logs/app.log", description="مسار ملف السجل")

    # ========== بوابات الدفع (Gateways) ==========
    STRIPE_API_KEY: Optional[str] = Field(default=None)
    STRIPE_WEBHOOK_SECRET: Optional[str] = Field(default=None)
    PAYMOB_API_KEY: Optional[str] = Field(default=None)

    # ========== الذكاء الاصطناعي (المساعد الصوتي والترجمة) ==========
    GOOGLE_API_KEY: Optional[str] = Field(
        default=None,
        description="مفتاح Google API لاستخدام Gemini (الترجمة، تحليل النية)"
    )
    # يمكنك إضافة مفاتيح أخرى للنماذج المفتوحة المصدر إن أردت
    # OLLAMA_URL: str = Field(default="http://localhost:11434")

    # ========== التحقق من صحة الإعدادات ==========
    @field_validator("SECRET_KEY")
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        if v == "CHANGE_ME_NOW":
            raise ValueError("يجب تغيير SECRET_KEY من القيمة الافتراضية في بيئة الإنتاج")
        return v

# إنشاء كائن الإعدادات العالمي (Singleton)
settings = Settings()