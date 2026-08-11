# app/core/config.py
import os
import json
import base64
import secrets
import logging
from typing import Optional, Dict, Any, List
from pydantic import Field, field_validator, SecretStr  # type: ignore[import]
from pydantic_settings import BaseSettings, SettingsConfigDict  # type: ignore[import]
from botocore.exceptions import ClientError  # type: ignore[import]
import boto3  # type: ignore[import]
from dotenv import load_dotenv  # type: ignore[import]

load_dotenv()

logger = logging.getLogger(__name__)

def load_secrets_from_aws() -> Dict[str, Any]:
    """
    جلب الأسرار من AWS Secrets Manager.
    في حال الفشل، يتم رفع استثناء لإيقاف التشغيل في البيئة الإنتاجية.
    """
    try:
        client = boto3.client('secretsmanager', region_name=os.getenv("AWS_REGION", "us-east-1"))
        response = client.get_secret_value(SecretId=os.getenv("SECRETS_ARN", "eppne/prod/secrets"))
        return json.loads(response['SecretString'])
    except ClientError as e:
        raise RuntimeError(f"Could not retrieve secrets from AWS: {e}") from e

def generate_encryption_key() -> str:
    """
    توليد مفتاح تشفير صالح لـ Fernet (32 بايت مشفرة Base64).
    يُستخدم فقط في بيئة التطوير إذا لم يُعرَّف المفتاح.
    """
    return base64.urlsafe_b64encode(secrets.token_bytes(32)).decode('utf-8')


class Settings(BaseSettings):
    # ============================================================
    # 1. الحقول الأساسية (مع قيم افتراضية آمنة للتطوير فقط)
    # ============================================================
    ENVIRONMENT: str = Field(default="development", pattern="^(development|staging|production)$")
    LOG_FILE: str = Field(default="app.log")
    LOG_LEVEL: str = Field(default="INFO", pattern="^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$")

    # ============================================================
    # 2. قاعدة البيانات (مع Validator صارم)
    # ============================================================
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://eppne:eppne123@localhost:5432/eppne",
        description="PostgreSQL Async URL (e.g., postgresql+asyncpg://user:pass@host:port/db)"
    )
    DATABASE_POOL_SIZE: int = Field(default=20, ge=1, le=100)
    DATABASE_MAX_OVERFLOW: int = Field(default=40, ge=0)

    @field_validator("DATABASE_URL")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        """تأكد من أن الرابط يستخدم مشغل asyncpg ويحتوي على منفذ."""
        if not v.startswith("postgresql+asyncpg://"):
            raise ValueError("DATABASE_URL must use 'postgresql+asyncpg://' driver.")
        # تحقق من وجود منفذ (رقم بعد آخر نقطتين)
        if ":" not in v.split("@")[-1]:
            raise ValueError("DATABASE_URL must include port number (e.g., :5432).")
        return v

    # ============================================================
    # 3. Redis (مع Validator صارم)
    # ============================================================
    REDIS_URL: str = Field(
        default="redis://localhost:6379/0",
        description="Redis URL (e.g., redis://:password@host:port/db)"
    )
    REDIS_PASSWORD: Optional[str] = Field(default=None, description="Redis password (optional, can be in URL)")
    REDIS_MAX_CONNECTIONS: int = Field(default=20, ge=5)

    @field_validator("REDIS_URL")
    @classmethod
    def validate_redis_url(cls, v: str) -> str:
        """تأكد من أن الرابط يبدأ بـ redis://."""
        if not v.startswith("redis://"):
            raise ValueError("REDIS_URL must start with 'redis://'.")
        return v

    # ============================================================
    # 4. JWT والأمان (إلزامية في الإنتاج، مع SecretStr)
    # ============================================================
    SECRET_KEY: SecretStr = Field(
        default=SecretStr("CHANGE_ME_NOW_CHANGE_ME_NOW_12345678"),
        min_length=32,
        description="JWT Secret Key (min 32 chars). MUST be changed in production."
    )
    ALGORITHM: str = Field(default="HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=10080, ge=1)
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=30, ge=1)

    # ============================================================
    # 5. مفتاح التشفير الإضافي (لـ Fernet / Automation)
    # ============================================================
    SECRET_ENCRYPTION_KEY: str = Field(
        default_factory=generate_encryption_key,
        description="Base64-encoded 32-byte encryption key for internal secrets."
    )

    @field_validator("SECRET_ENCRYPTION_KEY")
    @classmethod
    def validate_encryption_key(cls, v: str) -> str:
        """تأكد من أن المفتاح هو Base64 صالح لـ 32 بايت."""
        try:
            decoded = base64.urlsafe_b64decode(v)
            if len(decoded) != 32:
                raise ValueError("SECRET_ENCRYPTION_KEY must decode to exactly 32 bytes.")
        except Exception as e:
            raise ValueError(f"SECRET_ENCRYPTION_KEY must be a valid Base64-encoded 32-byte key: {e}") from e
        return v

    # ============================================================
    # 6. المستخدم السوبر (إلزامي في الإنتاج)
    # ============================================================
    FIRST_SUPERUSER_EMAIL: str = Field(
        default="admin@eppne.com",
        pattern=r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    )
    FIRST_SUPERUSER_PASSWORD: SecretStr = Field(
        default=SecretStr("ChangeMe@123"),
        min_length=8,
        description="Superuser password. MUST be changed in production."
    )
    FIRST_SUPERUSER_USERNAME: str = Field(default="sovereign_admin", min_length=3)
    FIRST_SUPERUSER_NAME_AR: str = Field(default="المدير التنفيذي")
    FIRST_SUPERUSER_NAME_EN: str = Field(default="Executive Director")

    # ============================================================
    # 6b. التسجيل العام (Public Self-Registration) — Phase 15
    # ============================================================
    PUBLIC_REGISTRATION_TENANT_ID: int = Field(
        default=1,
        description=(
            "التينانت الوحيد المسموح بالتسجيل العام المباشر فيه "
            "(POST /identity/register، بدون دعوة). قيمة tenant_id ثابتة من "
            "قاعدة البيانات، بمعزل تام عن أي دومين يُستخدم للوصول للسيرفر. "
            "إلزامي تعيينها صراحةً في .env في بيئة الإنتاج."
        )
    )

    # ============================================================
    # 7. العملات والتخزين
    # ============================================================
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

    # ============================================================
    # 8. تخزين الملفات (S3/MinIO)
    # ============================================================
    S3_ENDPOINT: str = Field(default="localhost:9000")
    S3_ACCESS_KEY: str = Field(default="minioadmin")
    S3_SECRET_KEY: str = Field(default="minioadmin")
    S3_BUCKET_MEDIA: str = Field(default="eppne-media")
    S3_BUCKET_CERTIFICATES: str = Field(default="eppne-certs")
    S3_USE_SSL: bool = Field(default=False)

    # ============================================================
    # 9. الشبكة والتوصيلات
    # ============================================================
    WS_HEARTBEAT_INTERVAL: int = Field(default=30, ge=5)
    RATE_LIMIT_PER_MINUTE: int = Field(default=60, ge=1)
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
    # 10. خصائص محسوبة (Computed Properties)
    # ============================================================
    @property
    def REFRESH_TOKEN_EXPIRE_MINUTES(self) -> int:
        """تحويل مدة صلاحية Refresh Token من أيام إلى دقائق."""
        return self.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60

    # ============================================================
    # 11. تكوين Pydantic
    # ============================================================
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # ============================================================
    # 12. المنشئ (مع تحميل AWS Secrets Manager)
    # ============================================================
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # -- تحميل الأسرار من AWS في بيئة الإنتاج --
        if self.ENVIRONMENT == "production":
            try:
                secrets_aws = load_secrets_from_aws()
                # تحديث الحقول الحساسة من AWS
                for key, value in secrets_aws.items():
                    if hasattr(self, key):
                        # إذا كان الحقل من نوع SecretStr، نلف القيمة به
                        if key in ("SECRET_KEY", "FIRST_SUPERUSER_PASSWORD"):
                            setattr(self, key, SecretStr(value))
                        else:
                            setattr(self, key, value)
                logger.info("✅ AWS Secrets loaded successfully for production environment.")
            except Exception as e:
                # في الإنتاج، يجب ألا نستمر إذا تعذر جلب الأسرار
                raise RuntimeError(f"Production startup failed: unable to load secrets - {e}") from e

        # -- تحقق أمني في الإنتاج --
        if self.ENVIRONMENT == "production":
            # التأكد من أن SECRET_KEY غير افتراضي
            if self.SECRET_KEY.get_secret_value() == "CHANGE_ME_NOW_CHANGE_ME_NOW_12345678":
                raise ValueError("❌ SECRET_KEY must be changed in production! (Default value is not allowed)")

            # التأكد من أن كلمة مرور السوبر غير افتراضية
            if self.FIRST_SUPERUSER_PASSWORD.get_secret_value() == "ChangeMe@123":
                raise ValueError("❌ FIRST_SUPERUSER_PASSWORD must be changed in production! (Default is not allowed)")

            # التأكد من أن PUBLIC_REGISTRATION_TENANT_ID اتعيّن صراحةً (مش الافتراضي الضمني)
            if os.getenv("PUBLIC_REGISTRATION_TENANT_ID") is None:
                raise ValueError(
                    "❌ PUBLIC_REGISTRATION_TENANT_ID must be set explicitly in .env for production! "
                    "(Implicit default is not allowed — this value determines which tenant public "
                    "self-registration writes into.)"
                )

            # التحقق من صحة مفتاح التشفير (تم عبر validator أعلاه، لكن نضعه هنا كتأكيد)
            try:
                base64.urlsafe_b64decode(self.SECRET_ENCRYPTION_KEY)
            except Exception as e:
                raise ValueError(f"❌ SECRET_ENCRYPTION_KEY is invalid: {e}") from e

        # -- تحذيرات في التطوير (استخدام logging بدلاً من print) --
        if self.ENVIRONMENT != "production":
            if self.SECRET_KEY.get_secret_value() == "CHANGE_ME_NOW_CHANGE_ME_NOW_12345678":
                logger.warning(
                    "⚠️  [DEV] Using default SECRET_KEY. "
                    "It is recommended to set a unique SECRET_KEY in .env file."
                )
            if self.FIRST_SUPERUSER_PASSWORD.get_secret_value() == "ChangeMe@123":
                logger.warning(
                    "⚠️  [DEV] Using default FIRST_SUPERUSER_PASSWORD. "
                    "It is recommended to set a unique password in .env file."
                )
            if os.getenv("PUBLIC_REGISTRATION_TENANT_ID") is None:
                logger.warning(
                    "⚠️  [DEV] Using default PUBLIC_REGISTRATION_TENANT_ID=%s. "
                    "Must be set explicitly in .env before production.",
                    self.PUBLIC_REGISTRATION_TENANT_ID,
                )
            # لا نتحقق من SECRET_ENCRYPTION_KEY في التطوير لأنه قد يكون مولّداً تلقائياً


# ============================================================
# 13. إنشاء كائن الإعدادات العام
# ============================================================
settings = Settings()