# app/domains/identity/service.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func
from typing import Optional, Dict, cast, Any
import uuid
from datetime import datetime
import json
import logging

from app.domains.identity.repository import UserRepository, WalletRepository
from app.domains.identity.models import User
from app.domains.finance.models import Wallet
from app.domains.identity.schemas import UserCreate, UserUpdate
from app.core.security import get_password_hash, verify_password
from app.domains.auth.jwt_service import jwt_service
from app.domains.auth.jwt_service import revoke_all_user_tokens, revoke_refresh_token, verify_refresh_token
from app.core.errors import PermissionDeniedError, NotFoundError, ValidationError
from app.core.logging_conf import logger

try:
    from app.core.redis_client import redis_client
except ImportError:
    redis_client = None
    logger.warning("Redis client not available. Caching disabled.")


async def delete_cached_user(user_id: int, tenant_id: int) -> None:
    if redis_client is None:
        return
    key = f"user:{user_id}:{tenant_id}"
    await redis_client.delete(key)


async def set_cached_user(user_id: int, tenant_id: int, data: dict) -> None:
    if redis_client is None:
        return
    key = f"user:{user_id}:{tenant_id}"
    await redis_client.setex(key, 3600, json.dumps(data, default=str))


async def get_cached_user(user_id: int, tenant_id: int) -> Optional[dict]:
    if redis_client is None:
        return None
    key = f"user:{user_id}:{tenant_id}"
    raw = await redis_client.get(key)
    if raw:
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return None
    return None


class UserService:
    def __init__(self, db: AsyncSession, tenant_id: int):
        self.db = db
        self.tenant_id = tenant_id
        self.user_repo = UserRepository(db)
        self.wallet_repo = WalletRepository(db)

    async def register(self, data: UserCreate, idempotency_key: Optional[str] = None) -> User:
        if idempotency_key:
            existing_user = await self.user_repo.get_by_idempotency_key(idempotency_key, self.tenant_id)
            if existing_user:
                logger.info(f"Duplicate registration blocked for key: {idempotency_key}")
                return existing_user

        existing = await self.user_repo.get_by_email(data.email, self.tenant_id)
        if existing:
            raise ValidationError("البريد الإلكتروني مسجل بالفعل")
        existing = await self.user_repo.get_by_username(data.username, self.tenant_id)
        if existing:
            raise ValidationError("اسم المستخدم مستخدم بالفعل")

        hashed = get_password_hash(data.password.get_secret_value())

        async with self.db.begin_nested():
            user = User(
                username=data.username,
                email=data.email,
                hashed_password=hashed,
                name_ar=data.name_ar,
                name_en=data.name_en,
                birth_date=data.birth_date,
                marriage_status=data.marriage_status,
                language_preference=data.language_preference,
                profile_metadata=data.profile_metadata or {},
                preferences=data.preferences or {},
                public_id=str(uuid.uuid4()),
                idempotency_key=idempotency_key,
                tenant_id=self.tenant_id
            )
            user = await self.user_repo.create(user)
            await self.wallet_repo.create(cast(int, user.id), self.tenant_id)

        await set_cached_user(cast(int, user.id), self.tenant_id, {
            "id": user.id,
            "tenant_id": user.tenant_id,
            "username": user.username,
            "email": user.email,
            "system_role": str(user.system_role),
            "is_active": user.is_active,
            "session_version": user.session_version,
        })
        return user

    async def authenticate(self, username_or_email: str, password: str, ip: Optional[str] = None, user_agent: Optional[str] = None) -> Optional[User]:
        user = await self.user_repo.get_by_username_or_email(username_or_email, self.tenant_id)
        if not user or not verify_password(password, user.hashed_password) or not user.is_active:
            return None

        await self.user_repo.update(cast(int, user.id), self.tenant_id, last_login_at=func.now(), last_login_ip=ip, last_login_user_agent=user_agent)
        await delete_cached_user(cast(int, user.id), self.tenant_id)
        return user

    async def generate_tokens(self, user: User) -> Dict[str, str]:
        access_token = jwt_service.create_access_token(
            user_id=cast(int, user.id),
            role=str(user.system_role),
            session_version=cast(int, user.session_version),
            tenant_id=self.tenant_id
        )
        refresh_token, _ = jwt_service.create_refresh_token(
            user_id=cast(int, user.id),
            session_version=cast(int, user.session_version),
            tenant_id=self.tenant_id
        )
        return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}

    async def refresh_tokens(self, refresh_token: str) -> Dict[str, str]:
        payload = verify_refresh_token(refresh_token)
        if not payload:
            raise PermissionDeniedError("انتهت صلاحية الجلسة")

        if not isinstance(payload, dict):
            raise PermissionDeniedError("Invalid token payload format")

        sub = payload.get("sub")
        if sub is None:
            raise PermissionDeniedError("Invalid token payload")
        user_id = int(sub)

        session_version = payload.get("sv")
        tenant_id_from_token = payload.get("tenant_id")

        if tenant_id_from_token != self.tenant_id:
            logger.warning(f"Tenant mismatch in refresh token: token={tenant_id_from_token}, request={self.tenant_id}")
            raise PermissionDeniedError("تعارض في المستأجر")

        user = await self.user_repo.get_by_id(user_id, self.tenant_id, load_wallet=True)
        if not user or not user.is_active:
            raise PermissionDeniedError("المستخدم غير نشط")

        if user.session_version != session_version:
            logger.warning(f"Session version mismatch for user {user_id}, revoking token")
            await revoke_refresh_token(refresh_token, self.tenant_id)
            await self.user_repo.increment_session_version(user_id, self.tenant_id)
            await delete_cached_user(user_id, self.tenant_id)
            raise PermissionDeniedError("تم إبطال الجلسة من مكان آخر، يرجى تسجيل الدخول مجدداً")

        await revoke_refresh_token(refresh_token, self.tenant_id)

        new_access_token = jwt_service.create_access_token(
            user_id=user_id,
            role=str(user.system_role),
            session_version=cast(int, user.session_version),
            tenant_id=self.tenant_id
        )
        new_refresh_token, _ = jwt_service.create_refresh_token(
            user_id=user_id,
            session_version=cast(int, user.session_version),
            tenant_id=self.tenant_id
        )
        return {"access_token": new_access_token, "refresh_token": new_refresh_token, "token_type": "bearer"}

    async def revoke_all_sessions(self, user_id: int) -> int:
        async with self.db.begin_nested():
            await self.user_repo.increment_session_version(user_id, self.tenant_id)
            await delete_cached_user(user_id, self.tenant_id)
            revoked_count = await revoke_all_user_tokens(user_id, self.tenant_id)
        return revoked_count

    async def revoke_specific_refresh_token(self, refresh_token: str) -> None:
        await revoke_refresh_token(refresh_token, self.tenant_id)

    async def get_user(self, user_id: int) -> User:
        cached = await get_cached_user(user_id, self.tenant_id)
        if cached and isinstance(cached, dict):
            user = User()
            for k, v in cached.items():
                setattr(user, k, v)
            return user

        user = await self.user_repo.get_by_id(user_id, self.tenant_id, load_wallet=True)
        if not user:
            raise NotFoundError("المستخدم غير موجود")
        await set_cached_user(user_id, self.tenant_id, {
            "id": user.id,
            "tenant_id": user.tenant_id,
            "username": user.username,
            "email": user.email,
            "system_role": str(user.system_role),
            "is_active": user.is_active,
            "session_version": user.session_version
        })
        return user

    async def get_current_user(self, user_id: int) -> User:
        return await self.get_user(user_id)

    async def update_user(self, user_id: int, data: UserUpdate) -> User:
        update_data = data.model_dump(exclude_unset=True)
        forbidden = {"id", "public_id", "hashed_password", "system_role", "sovereign_rank", "tenant_id"}
        for f in forbidden:
            update_data.pop(f, None)

        logger.info(f"User update for user_id={user_id}, fields={list(update_data.keys())}", extra={"trace_id": str(uuid.uuid4()), "tenant_id": self.tenant_id})
        user = await self.user_repo.update(user_id, self.tenant_id, **update_data)
        if not user:
            raise NotFoundError("المستخدم غير موجود")
        await delete_cached_user(user_id, self.tenant_id)
        await set_cached_user(user_id, self.tenant_id, {
            "id": user.id,
            "tenant_id": user.tenant_id,
            "username": user.username,
            "email": user.email,
            "system_role": str(user.system_role),
            "is_active": user.is_active,
            "session_version": user.session_version
        })
        return user

    async def change_password(self, user_id: int, old_password: str, new_password: str) -> bool:
        user = await self.user_repo.get_by_id(user_id, self.tenant_id)
        if not user or not verify_password(old_password, user.hashed_password):
            logger.warning(f"Failed password change for user_id={user_id}", extra={"trace_id": str(uuid.uuid4()), "tenant_id": self.tenant_id})
            raise PermissionDeniedError("كلمة المرور الحالية غير صحيحة")

        new_hashed = get_password_hash(new_password)
        async with self.db.begin_nested():
            await self.user_repo.update(user_id, self.tenant_id, hashed_password=new_hashed)
            await self.user_repo.increment_session_version(user_id, self.tenant_id)

        await delete_cached_user(user_id, self.tenant_id)
        await revoke_all_user_tokens(user_id, self.tenant_id)
        logger.info(f"Password changed for user_id={user_id}", extra={"trace_id": str(uuid.uuid4()), "tenant_id": self.tenant_id})
        return True

    async def soft_delete_account(self, user_id: int, password: str) -> bool:
        user = await self.user_repo.get_by_id(user_id, self.tenant_id)
        if not user or not verify_password(password, user.hashed_password):
            logger.warning(f"Unauthorized soft delete for user_id={user_id}", extra={"trace_id": str(uuid.uuid4()), "tenant_id": self.tenant_id})
            raise PermissionDeniedError("كلمة المرور غير صحيحة")

        async with self.db.begin_nested():
            await self.user_repo.update(user_id, self.tenant_id, is_active=False)
            await self.user_repo.increment_session_version(user_id, self.tenant_id)

        await delete_cached_user(user_id, self.tenant_id)
        await revoke_all_user_tokens(user_id, self.tenant_id)
        logger.critical(f"Account soft-deleted for user_id={user_id}", extra={"trace_id": str(uuid.uuid4()), "tenant_id": self.tenant_id})
        return True