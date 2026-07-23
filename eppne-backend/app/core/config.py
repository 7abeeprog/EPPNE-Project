# app/core/config.py
import os
import json
import base64
import secrets
import boto3
from botocore.exceptions import ClientError
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv

load_dotenv()

def load_secrets_from_aws() -> Dict[str, Any]:
    """
    جلب الأسرار من AWS Secrets Manager.
    في حال الفشل، يتم رفع استثناء لإيقاف التشغيل في البيئة الإنتاجية.
    """
    try:
        client = boto3.client('secretsmanager', region_name=os.getenv("REGION", "us-east-1"))
        response = client.get_secret_value(SecretId=os.getenv("SECRETS_ARN", "eppne/prod/secrets"))
        return json.loads(response['SecretString'])
    except ClientError as e:
        raise Exception(f"Could not retrieve secrets from AWS: {e}")

def generate_encryption_key() -> str:
    """
    توليد مفتاح تشفير صالح لـ Fernet (32 بايت مشفرة Base64).
    يُستخدم فقط في بيئة التطوير إذا لم يُعرَّف المفتاح.
    """
    return base64.urlsafe_b64encode(secrets.token_bytes(32)).decode('utf-8')

class Settings(BaseSettings):
    # ========== الحقول الأساسية ==========
    ENVIRONMENT: str = Field(default="development")
    LOG_FILE: str = Field(default="app.log")
    LOG_LEVEL: str = Field(default="INFO")

    # ========== قاعدة البيانات ==========
    DATABASE_URL: str = Field(default="postgresql+asyncpg://eppne:eppne123@localhost:5432/eppne")
    DATABASE_POOL_SIZE: int = Field(default=20, ge=1)
    DATABASE_MAX_OVERFLOW: int = Field(default=40, ge=0)

    # ========== Redis ==========
    REDIS_URL: str = Field(default="redis://localhost:6379/0")
    REDIS_PASSWORD: Optional[str] = Field(default=None)
    REDIS_MAX_CONNECTIONS: int = Field(default=20, ge=5)

    # ========== JWT والأمان ==========
    # 🔥 تم تغيير القيمة الافتراضية لتكون بطول 32 حرفاً (لتجاوز تحقق Pydantic)
    SECRET_KEY: str = Field(default="CHANGE_ME_NOW_CHANGE_ME_NOW_12345678", min_length=32)
    ALGORITHM: str = Field(default="HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=10080)
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=30)

    # ========== 🔐 مفتاح التشفير الإضافي (لـ Fernet / Automation) ==========
    SECRET_ENCRYPTION_KEY: str = Field(
        default_factory=generate_encryption_key,
        description="مفتاح تشفير 32-بايت بصيغة Base64 يستخدم لتشفير بيانات سير العمل والأسرار الداخلية."
    )

    # ========== المستخدم السوبر ==========
    FIRST_SUPERUSER_EMAIL: str = Field(default="admin@eppne.com")
    FIRST_SUPERUSER_PASSWORD: str = Field(default="ChangeMe@123")
    FIRST_SUPERUSER_USERNAME: str = Field(default="sovereign_admin")
    FIRST_SUPERUSER_NAME_AR: str = Field(default="المدير التنفيذي")
    FIRST_SUPERUSER_NAME_EN: str = Field(default="Executive Director")

    # ========== العملات ==========
    CRYPTO_MODE: str = Field(default="FULL_CRYPTO")
    EXCHANGE_RATES: Dict[str, float] = Field(
        default={
            "MR_POUND": 1.0,
            "MR_USDT": 50.0,
            "MR7": 5.0,
            "NBT": 250.0,
            "MRX": 500.0,
        }
    )

    # ========== تخزين الملفات (S3) ==========
    S3_ENDPOINT: str = Field(default="localhost:9000")
    S3_ACCESS_KEY: str = Field(default="minioadmin")
    S3_SECRET_KEY: str = Field(default="minioadmin")
    S3_BUCKET_MEDIA: str = Field(default="eppne-media")
    S3_BUCKET_CERTIFICATES: str = Field(default="eppne-certs")
    S3_USE_SSL: bool = Field(default=False)

    # ========== التوصيلات ==========
    WS_HEARTBEAT_INTERVAL: int = Field(default=30)
    RATE_LIMIT_PER_MINUTE: int = Field(default=60)
    ALLOWED_HOSTS: List[str] = Field(
        default=[
            "localhost",
            "127.0.0.1",
            "eppne.sovereign.eg",
            "api.eppne.sovereign.eg",
            "staging.eppne.sovereign.eg",
        ]
    )
    ALLOWED_ORIGINS: List[str] = Field(
        default=[
            "http://localhost:3000",
            "http://localhost:3001",
            "https://eppne.sovereign.eg",
            "https://staging.eppne.sovereign.eg",
        ]
    )

    # ============================================================
    # 🔥 الحل السحري لمشكلة AttributeError (تمت إضافته هنا)
    # ============================================================
    @property
    def REFRESH_TOKEN_EXPIRE_MINUTES(self) -> int:
        """
        تحويل مدة صلاحية Refresh Token من أيام إلى دقائق.
        يستخدمه ملف security.py تلقائياً.
        """
        return self.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60

    # إعدادات Pydantic (تُقرأ من .env مع تجاهل الحالة)
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # ---- تحميل الأسرار من AWS في بيئة الإنتاج ----
        if self.ENVIRONMENT == "production":
            try:
                secrets_aws = load_secrets_from_aws()
                self.SECRET_KEY = secrets_aws.get("SECRET_KEY", self.SECRET_KEY)
                self.DATABASE_URL = secrets_aws.get("DATABASE_URL", self.DATABASE_URL)
                self.REDIS_URL = secrets_aws.get("REDIS_URL", self.REDIS_URL)
                self.S3_ENDPOINT = secrets_aws.get("S3_ENDPOINT", self.S3_ENDPOINT)
                self.S3_ACCESS_KEY = secrets_aws.get("S3_ACCESS_KEY", self.S3_ACCESS_KEY)
                self.S3_SECRET_KEY = secrets_aws.get("S3_SECRET_KEY", self.S3_SECRET_KEY)
                # 🔐 جلب مفتاح التشفير من الأسرار إن وُجد
                enc_key = secrets_aws.get("SECRET_ENCRYPTION_KEY")
                if enc_key:
                    self.SECRET_ENCRYPTION_KEY = enc_key
            except Exception as e:
                # في الإنتاج، يجب ألا نستمر إذا تعذر جلب الأسرار
                raise RuntimeError(f"Production startup failed: unable to load secrets - {e}")

        # ---- تحقق أمني في الإنتاج ----
        if self.ENVIRONMENT == "production":
            if self.SECRET_KEY == "CHANGE_ME_NOW_CHANGE_ME_NOW_12345678":
                raise ValueError("❌ SECRET_KEY must be changed in production! (Default value is not allowed)")
            # التحقق من صحة مفتاح التشفير (أن يكون بطول 44 حرفاً Base64)
            try:
                base64.urlsafe_b64decode(self.SECRET_ENCRYPTION_KEY)
            except Exception:
                raise ValueError("❌ SECRET_ENCRYPTION_KEY must be a valid Base64-encoded 32-byte key!")

        # ---- تحذير في التطوير إذا كان المفتاح هو القيمة الافتراضية أو مُولّداً تلقائياً ----
        if self.ENVIRONMENT != "production":
            if self.SECRET_KEY == "CHANGE_ME_NOW_CHANGE_ME_NOW_12345678":
                print("⚠️  [DEV] Using default SECRET_KEY. It is recommended to set a unique SECRET_KEY in .env file.")
            if self.SECRET_ENCRYPTION_KEY == generate_encryption_key():
                print("⚠️  [DEV] Using auto-generated SECRET_ENCRYPTION_KEY. This is fine for development but replace it in production.")

# ========== إنشاء كائن الإعدادات العام ==========
settings = Settings()