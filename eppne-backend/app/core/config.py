# app/core/config.py
import os
import json
import boto3
from botocore.exceptions import ClientError
from pydantic_settings import BaseSettings
from pydantic import Field, ConfigDict
from typing import Optional, Dict, Any
from dotenv import load_dotenv

# تحميل متغيرات .env محلياً (للتطوير فقط)
load_dotenv()

def load_secrets_from_aws() -> Dict[str, Any]:
    """تحميل الأسرار من AWS Secrets Manager."""
    try:
        client = boto3.client('secretsmanager', region_name=os.getenv("REGION", "us-east-1"))
        response = client.get_secret_value(SecretId=os.getenv("SECRETS_ARN", "eppne/prod/secrets"))
        return json.loads(response['SecretString'])
    except ClientError as e:
        raise Exception(f"Could not retrieve secrets from AWS: {e}")

class Settings(BaseSettings):
    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False
    )

    # ========== البيئة ==========
    ENVIRONMENT: str = Field(default="development")

    # ========== قاعدة البيانات ==========
    DATABASE_URL: str = Field(default="postgresql+asyncpg://eppne:eppne123@localhost:5432/eppne")
    DATABASE_POOL_SIZE: int = Field(default=20, ge=1)
    DATABASE_MAX_OVERFLOW: int = Field(default=40, ge=0)

    # ========== Redis ==========
    REDIS_URL: str = Field(default="redis://localhost:6379/0")
    REDIS_PASSWORD: Optional[str] = Field(default=None)
    REDIS_MAX_CONNECTIONS: int = Field(default=20, ge=5)

    # ========== JWT ==========
    SECRET_KEY: str = Field(default="CHANGE_ME_NOW", min_length=32)
    ALGORITHM: str = Field(default="HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=10080)
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=30)

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

    # ========== تخزين الملفات ==========
    S3_ENDPOINT: str = Field(default="localhost:9000")
    S3_ACCESS_KEY: str = Field(default="minioadmin")
    S3_SECRET_KEY: str = Field(default="minioadmin")
    S3_BUCKET_MEDIA: str = Field(default="eppne-media")
    S3_BUCKET_CERTIFICATES: str = Field(default="eppne-certs")
    S3_USE_SSL: bool = Field(default=False)

    # ========== WebSocket ==========
    WS_HEARTBEAT_INTERVAL: int = Field(default=30)

    # ========== تحديد المعدل ==========
    RATE_LIMIT_PER_MINUTE: int = Field(default=60)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # إذا كانت البيئة إنتاج، اسحب الأسرار من AWS Secrets Manager
        if self.ENVIRONMENT == "production":
            secrets = load_secrets_from_aws()
            # استبدال القيم الحساسة من الأسرار
            self.SECRET_KEY = secrets.get("SECRET_KEY", self.SECRET_KEY)
            self.DATABASE_URL = secrets.get("DATABASE_URL", self.DATABASE_URL)
            self.REDIS_URL = secrets.get("REDIS_URL", self.REDIS_URL)
            self.S3_ENDPOINT = secrets.get("S3_ENDPOINT", self.S3_ENDPOINT)
            self.S3_ACCESS_KEY = secrets.get("S3_ACCESS_KEY", self.S3_ACCESS_KEY)
            self.S3_SECRET_KEY = secrets.get("S3_SECRET_KEY", self.S3_SECRET_KEY)

settings = Settings()