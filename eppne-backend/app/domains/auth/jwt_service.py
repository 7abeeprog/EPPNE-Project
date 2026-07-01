# app/domains/auth/jwt_service.py
import os
import json
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, Tuple
import base64

from jose import jwt, JWTError
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend

from app.core.config import settings
from app.core.logging_conf import logger

class JWTService:
    """
    خدمة JWT باستخدام خوارزمية RS256 (تشفير غير متماثل).
    🔥 الأمان: استخدام مفاتيح عامة/خاصة يضمن أن الخدمات المصغرة يمكنها التحقق
    من صحة التوكنات دون الحاجة إلى الاتصال بقاعدة البيانات.
    🔥 المعيار: متوافق مع OAuth2 و OpenID Connect.
    """

    def __init__(self):
        self.algorithm = "RS256"
        self._keys_loaded = False  # ✅ تأخير تحميل المفاتيح إلى أول استخدام
        # لا نقوم بتحميل المفاتيح هنا لتجنب مشاكل التهيئة المبكرة

    def _ensure_keys_loaded(self) -> None:
        """
        التأكد من تحميل المفاتيح والإعدادات قبل الاستخدام.
        يتم استدعاؤها في بداية كل دالة عامة تحتاج إلى المفاتيح.
        """
        if self._keys_loaded:
            return

        # تحميل الإعدادات من البيئة
        self.access_token_expire_minutes = getattr(settings, 'ACCESS_TOKEN_EXPIRE_MINUTES', 60)
        self.refresh_token_expire_days = getattr(settings, 'REFRESH_TOKEN_EXPIRE_DAYS', 30)

        # تحميل المفاتيح
        self._load_keys()
        self._keys_loaded = True
        logger.info("JWT keys loaded successfully (lazy loading)")

    def _load_keys(self) -> None:
        """
        تحميل مفاتيح التشفير من متغيرات البيئة.
        🔥 الأمان: في الإنتاج، استخدم Vault أو AWS KMS لتخزين المفاتيح.
        """
        try:
            # قراءة المفتاح الخاص (Private Key)
            private_key_pem = settings.PRIVATE_KEY
            if not private_key_pem:
                raise ValueError("PRIVATE_KEY is not set in environment")

            self.private_key = serialization.load_pem_private_key(
                private_key_pem.encode(),
                password=None,
                backend=default_backend()
            )

            # قراءة المفتاح العام (Public Key)
            public_key_pem = settings.PUBLIC_KEY
            if not public_key_pem:
                raise ValueError("PUBLIC_KEY is not set in environment")

            self.public_key = serialization.load_pem_public_key(
                public_key_pem.encode(),
                backend=default_backend()
            )

            logger.info("JWT keys loaded successfully (RS256)")

        except Exception as e:
            logger.error(f"Failed to load JWT keys: {str(e)}")
            # في حالة التطوير، يمكن توليد مفاتيح مؤقتة
            if settings.ENVIRONMENT == "development":
                self._generate_temp_keys()
            else:
                raise

    def _generate_temp_keys(self) -> None:
        """
        توليد مفاتيح مؤقتة للبيئة التطويرية (Development).
        ⚠️ تحذير: هذه المفاتيح غير آمنة ولا يجب استخدامها في الإنتاج!
        """
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.hazmat.primitives import serialization as crypto_serialization

        logger.warning("Generating temporary RSA keys for development!")

        # توليد مفتاح RSA 2048
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
            backend=default_backend()
        )

        # تنسيق المفتاح الخاص (PEM)
        private_pem = private_key.private_bytes(
            encoding=crypto_serialization.Encoding.PEM,
            format=crypto_serialization.PrivateFormat.PKCS8,
            encryption_algorithm=crypto_serialization.NoEncryption()
        )

        # تنسيق المفتاح العام (PEM)
        public_pem = private_key.public_key().public_bytes(
            encoding=crypto_serialization.Encoding.PEM,
            format=crypto_serialization.PublicFormat.SubjectPublicKeyInfo
        )

        self.private_key = private_key
        self.public_key = private_key.public_key()

        # تخزين المفاتيح في الذاكرة للتطوير فقط
        self._dev_private_pem = private_pem.decode()
        self._dev_public_pem = public_pem.decode()

        logger.info("Temporary keys generated for development")

    def create_access_token(self, user_id: int, role: str, session_version: int) -> str:
        """
        إنشاء Access Token صالح لمدة قصيرة (دقائق).
        🔥 الأمان: يحتوي فقط على user_id و role و session_version.
        🔥 يمنع منعاً باتاً وضع بيانات حساسة (email, phone) في الـ Payload.
        """
        self._ensure_keys_loaded()  # ✅ تأكد من تحميل المفاتيح
        payload = {
            "sub": str(user_id),
            "role": role,
            "sv": session_version,  # session_version للتحقق من صلاحية الجلسة
            "typ": "access",
            "iat": int(datetime.now(timezone.utc).timestamp()),
            "exp": int((datetime.now(timezone.utc) + timedelta(minutes=self.access_token_expire_minutes)).timestamp()),
        }
        return self._sign(payload)

    def create_refresh_token(self, user_id: int, session_version: int) -> Tuple[str, datetime]:
        """
        إنشاء Refresh Token صالح لمدة أطول (أيام).
        🔥 الأمان: يتم إرجاع التوكين كـ string، ويتم تخزين Hash فقط في قاعدة البيانات.
        """
        self._ensure_keys_loaded()  # ✅ تأكد من تحميل المفاتيح
        expires_at = datetime.now(timezone.utc) + timedelta(days=self.refresh_token_expire_days)
        payload = {
            "sub": str(user_id),
            "sv": session_version,
            "typ": "refresh",
            "iat": int(datetime.now(timezone.utc).timestamp()),
            "exp": int(expires_at.timestamp()),
        }
        return self._sign(payload), expires_at

    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        التحقق من صحة التوكن وتفكيكه.
        🔥 إرجاع None إذا كان التوكن غير صالح أو منتهي الصلاحية.
        """
        self._ensure_keys_loaded()  # ✅ تأكد من تحميل المفاتيح
        try:
            payload = jwt.decode(
                token,
                self.public_key,
                algorithms=[self.algorithm],
                options={"verify_signature": True, "verify_exp": True}
            )
            return payload
        except JWTError as e:
            logger.warning(f"JWT verification failed: {str(e)}")
            return None

    def _sign(self, payload: Dict[str, Any]) -> str:
        """توقيع الـ Payload باستخدام المفتاح الخاص."""
        try:
            return jwt.encode(
                payload,
                self.private_key,
                algorithm=self.algorithm
            )
        except Exception as e:
            logger.error(f"JWT signing failed: {str(e)}")
            raise ValueError("Failed to sign JWT")

    def get_token_type(self, token: str) -> Optional[str]:
        """استخراج نوع التوكن (access/refresh) من الـ Payload."""
        self._ensure_keys_loaded()  # ✅ تأكد من تحميل المفاتيح
        payload = self.verify_token(token)
        if not payload:
            return None
        return payload.get("typ")

    def get_user_id_from_token(self, token: str) -> Optional[int]:
        """استخراج user_id من التوكن."""
        self._ensure_keys_loaded()  # ✅ تأكد من تحميل المفاتيح
        payload = self.verify_token(token)
        if not payload:
            return None
        try:
            return int(payload.get("sub"))
        except (ValueError, TypeError):
            return None

    def get_session_version(self, token: str) -> Optional[int]:
        """استخراج session_version من التوكن."""
        self._ensure_keys_loaded()  # ✅ تأكد من تحميل المفاتيح
        payload = self.verify_token(token)
        if not payload:
            return None
        return payload.get("sv")

    def get_public_key_pem(self) -> str:
        """إرجاع المفتاح العام بتنسيق PEM (للخدمات المصغرة)."""
        self._ensure_keys_loaded()  # ✅ تأكد من تحميل المفاتيح
        if hasattr(self, "_dev_public_pem"):
            return self._dev_public_pem
            
        # 🔥 تعديل استراتيجي: عمل Caching لنتيجة الـ Serialization في الذاكرة 
        # لمنع استنزاف المعالج (CPU) عند كثرة استدعاء المفتاح من الخدمات الأخرى.
        if not hasattr(self, "_cached_public_pem"):
            self._cached_public_pem = self.public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            ).decode()
            
        return self._cached_public_pem


# 🔥 إنشاء مثيل واحد من الخدمة (Singleton) لإعادة الاستخدام
jwt_service = JWTService()