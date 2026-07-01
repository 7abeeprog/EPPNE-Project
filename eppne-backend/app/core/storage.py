# app/core/storage.py
import boto3
import logging
from botocore.client import Config
from app.core.config import settings
from minio import Minio
from minio.error import S3Error

logger = logging.getLogger(__name__)

# --- 🟢 هندسة الروابط لتتوافق مع صرامة Boto3 و MinIO ---
boto_endpoint = settings.S3_ENDPOINT
if not boto_endpoint.startswith("http"):
    scheme = "https://" if settings.S3_USE_SSL else "http://"
    boto_endpoint = f"{scheme}{boto_endpoint}"

# MinIO يرفض وجود http:// أو https://
minio_endpoint = settings.S3_ENDPOINT.replace("http://", "").replace("https://", "")

# --- إعدادات Boto3 ---
s3_client = boto3.client(
    "s3",
    endpoint_url=boto_endpoint,
    aws_access_key_id=settings.S3_ACCESS_KEY,
    aws_secret_access_key=settings.S3_SECRET_KEY,
    config=Config(signature_version="s3v4"),
    use_ssl=settings.S3_USE_SSL
)

# --- إعدادات MinIO ---
minio_client = Minio(
    minio_endpoint,
    access_key=settings.S3_ACCESS_KEY,
    secret_key=settings.S3_SECRET_KEY,
    secure=settings.S3_USE_SSL
)

def ensure_bucket_exists(bucket_name: str):
    """تأمين حاوية التخزين السيادية"""
    try:
        if not minio_client.bucket_exists(bucket_name):
            minio_client.make_bucket(bucket_name)
            logger.info(f"تم إنشاء حاوية تخزين جديدة: {bucket_name}")
            
            # جعل الحاوية عامة للقراءة (مهم للصور المصغرة للكورسات)
            policy = f"""{{
                "Version": "2012-10-17",
                "Statement": [
                    {{
                        "Effect": "Allow",
                        "Principal": {{"AWS": "*"}},
                        "Action": ["s3:GetObject"],
                        "Resource": ["arn:aws:s3:::{bucket_name}/*"]
                    }}
                ]
            }}"""
            minio_client.set_bucket_policy(bucket_name, policy)
            
    except S3Error as err:
        logger.error(f"خطأ في الوصول إلى MinIO: {err}")

async def upload_file(content: bytes, bucket: str, key: str, public: bool = False) -> str:
    """رفع ملف إلى MinIO/S3 وإرجاع الرابط."""
    
    # تأمين وجود الحاوية وتطبيق الصلاحيات قبل الرفع
    ensure_bucket_exists(bucket)

    extra_args = {"ACL": "public-read"} if public else {}
    s3_client.put_object(Bucket=bucket, Key=key, Body=content, **extra_args)
    
    if public:
        return f"{boto_endpoint}/{bucket}/{key}"
    else:
        # إرجاع رابط مؤقت أو داخلي
        return f"{boto_endpoint}/{bucket}/{key}"