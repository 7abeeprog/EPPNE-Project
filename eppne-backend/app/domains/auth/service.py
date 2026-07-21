# app/domains/auth/service.py

from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone
from typing import Optional, Tuple, Dict, Any, List, cast

from passlib.context import CryptContext

from sqlalchemy import select
# تأكد من تعديل مسار الاستيراد أدناه ليتطابق مع مسار ملف models.py الذي أرسلته لي
from app.domains.sovereign_entities.models import SovereignEntity, EntityRepresentative

from app.domains.auth.repository import AuthRepository
from app.domains.auth.jwt_service import jwt_service
from app.domains.auth.models import RefreshToken
from app.domains.identity.models import User
from app.core.errors import (
    AuthenticationError,
    NotFoundError,
    PermissionDeniedError,
    ValidationError
)
import logging
logger = logging.getLogger(__name__)

# 🔥 إعداد سياق التشفير لكلمات المرور (bcrypt)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = AuthRepository(db)

    # ==========================================
    # 1. المصادقة (Authentication)
    # ==========================================

    async def authenticate_user(self, username: str, password: str) -> User:
        """
        مصادقة المستخدم باستخدام اسم المستخدم أو البريد الإلكتروني.
        🔥 الأمان: استخدام bcrypt للتحقق من كلمة المرور.
        """
        # البحث عن المستخدم باسم المستخدم أو البريد الإلكتروني
        from app.domains.identity.repository import UserRepository
        user_repo = UserRepository(self.db)

        user = await user_repo.get_by_username_or_email(username)

        if not user:
            logger.warning(f"Authentication failed: user not found '{username}'")
            raise AuthenticationError("Invalid username or password")

        if not user.is_active:  # type: ignore
            logger.warning(f"Authentication failed: user inactive '{user.id}'")
            raise AuthenticationError("Account is disabled")

        # التحقق من كلمة المرور
        if not self._verify_password(password, user.hashed_password):  # type: ignore
            logger.warning(f"Authentication failed: invalid password for user '{user.id}'")
            raise AuthenticationError("Invalid username or password")

        # تحديث آخر تسجيل دخول
        await user_repo.update_last_login(user.id)

        return user

    async def create_session(
        self,
        user: User,
        device_name: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        إنشاء جلسة جديدة للمستخدم.
        🔥 جلب الـ tenant_id ديناميكياً بناءً على ارتباط المستخدم بالكيانات السيادية.
        """
        
        # 1. الاستعلام الذكي لجلب tenant_id من الكيانات المرتبطة بالمستخدم
        stmt = (
            select(SovereignEntity.tenant_id)
            .join(EntityRepresentative, EntityRepresentative.entity_id == SovereignEntity.id)
            .where(EntityRepresentative.user_id == user.id)
            .where(EntityRepresentative.is_active == True)
            .limit(1)  # نجلب النطاق الأساسي أو الأول
        )
        result = await self.db.execute(stmt)
        active_tenant_id = result.scalar_one_or_none()

       # 2. إنشاء التوكنز
        access_token = jwt_service.create_access_token(
            user_id=cast(int, user.id),
            role=user.system_role,  # type: ignore
            session_version=user.session_version  # type: ignore
        )

        refresh_token, expires_at = jwt_service.create_refresh_token(
            user_id=cast(int, user.id),
            session_version=user.session_version  # type: ignore
        )

        # 3. تخزين الـ Refresh Token
        await self.repo.create_refresh_token(
            user_id=cast(int, user.id),
            token=refresh_token,
            expires_at=expires_at,
            device_name=device_name,
            ip_address=ip_address,
            user_agent=user_agent
        )

        # 4. إرجاع البيانات المعمارية السليمة
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "Bearer",
            "expires_in": jwt_service.access_token_expire_minutes * 60,
            "user": {
                "id": cast(int, user.id),
                "username": user.username,  # type: ignore
                "email": user.email,  # type: ignore
                "role": user.system_role,  # type: ignore
                "sovereign_rank": user.sovereign_rank,  # type: ignore
                "tenant_id": active_tenant_id,
            }
        }
    
    async def refresh_access_token(self, refresh_token: str) -> Dict[str, Any]:
        """
        تجديد Access Token باستخدام Refresh Token.
        🔥 الأمان: يتم إبطال Refresh Token القديم وإنشاء واحد جديد (Token Rotation).
        """
        # 1. التحقق من صحة Refresh Token
        payload = jwt_service.verify_token(refresh_token)
        if not payload:
            raise AuthenticationError("Invalid or expired refresh token")

        if payload.get("typ") != "refresh":
            raise AuthenticationError("Invalid token type")

        user_id = int(cast(str, payload.get("sub")))
        session_version = payload.get("sv")  # قد يكون None

        # 2. جلب المستخدم
        from app.domains.identity.repository import UserRepository
        user_repo = UserRepository(self.db)
        user = await user_repo.get_by_id(user_id)

        if not user or not user.is_active:  # type: ignore
            raise AuthenticationError("User not found or inactive")

        # 3. التحقق من session_version
        if user.session_version != session_version:  # type: ignore
            raise AuthenticationError("Session has been revoked")

        # 4. البحث عن Refresh Token في قاعدة البيانات
        stored_token = await self.repo.get_refresh_token(refresh_token)

        if not stored_token:
            raise AuthenticationError("Refresh token not found")

        if stored_token.is_expired():
            # سيتم جدولة الحذف عبر Celery
            raise AuthenticationError("Refresh token expired")

        if stored_token.revoked:  # type: ignore
            raise AuthenticationError("Refresh token revoked")

        # 5. 🔥 Token Rotation: إبطال التوكين القديم وإنشاء توكين جديد
        await self.repo.revoke_refresh_token(refresh_token)

# 6. إنشاء Access Token جديد
        new_access_token = jwt_service.create_access_token(
            user_id=cast(int, user.id),
            role=user.system_role,  # type: ignore
            session_version=user.session_version  # type: ignore
        )

        # 7. إنشاء Refresh Token جديد
        new_refresh_token, expires_at = jwt_service.create_refresh_token(
            user_id=cast(int, user.id),
            session_version=user.session_version  # type: ignore
        )

        # 8. تخزين Refresh Token الجديد
        await self.repo.create_refresh_token(
            user_id=cast(int, user.id),
            token=new_refresh_token,
            expires_at=expires_at,
            device_name=stored_token.device_name,  # type: ignore
            ip_address=stored_token.ip_address,  # type: ignore
            user_agent=stored_token.user_agent  # type: ignore
        )
        
        return {
            "access_token": new_access_token,
            "refresh_token": new_refresh_token,
            "token_type": "Bearer",
            "expires_in": jwt_service.access_token_expire_minutes * 60,
        }

    async def revoke_session(self, user_id: int, refresh_token: str) -> bool:
        """
        إبطال جلسة محددة (تسجيل الخروج من جهاز معين).
        """
        stored_token = await self.repo.get_refresh_token(refresh_token)

        if not stored_token or stored_token.user_id != user_id:  # type: ignore
            return False

        if stored_token.revoked or stored_token.is_expired():  # type: ignore
            return False

        await self.repo.revoke_refresh_token(refresh_token)
        return True

    async def revoke_all_sessions(self, user_id: int) -> int:
        """
        إبطال جميع جلسات المستخدم (تسجيل الخروج من جميع الأجهزة).
        🔥 زيادة session_version يضمن إبطال جميع التوكنات الحالية.
        """
        # 1. إبطال جميع Refresh Tokens
        revoked_count = await self.repo.revoke_all_user_tokens(user_id)

        # 2. زيادة session_version (إبطال جميع Access Tokens)
        await self.repo.increment_session_version(user_id)

        return revoked_count

    async def get_active_sessions(
        self,
        user_id: int,
        skip: int = 0,
        limit: int = 20
    ) -> List[RefreshToken]:
        """
        جلب جميع الجلسات النشطة للمستخدم (للتدقيق الأمني).
        """
        tokens = await self.repo.list_user_refresh_tokens(
            user_id=user_id,
            skip=skip,
            limit=limit,
            include_revoked=False
        )
        return tokens

    # ==========================================
    # 2. دوال مساعدة
    # ==========================================

    def _verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """التحقق من صحة كلمة المرور باستخدام bcrypt."""
        return pwd_context.verify(plain_password, hashed_password)

    def _hash_password(self, password: str) -> str:
        """تشفير كلمة المرور باستخدام bcrypt."""
        return pwd_context.hash(password)