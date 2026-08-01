# app/domains/auth/service.py
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone
from typing import Optional, Tuple, Dict, Any, List, cast

from passlib.context import CryptContext
from sqlalchemy import select

from app.domains.auth.repository import AuthRepository
from app.domains.auth.jwt_service import jwt_service
from app.domains.auth.models import RefreshToken
from app.domains.identity.models import User
from app.domains.identity.repository import UserRepository
from app.domains.sovereign_entities.models import SovereignEntity, EntityRepresentative
from app.core.errors import (
    AuthenticationError,
    NotFoundError,
    PermissionDeniedError,
    ValidationError
)
from app.core.redis_client import redis_client
import logging

logger = logging.getLogger(__name__)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthService:
    def __init__(self, db: AsyncSession, tenant_id: int):
        self.db = db
        self.tenant_id = tenant_id
        self.repo = AuthRepository(db)
        self.user_repo = UserRepository(db)

    async def authenticate_user(self, username: str, password: str) -> User:
        user = await self.user_repo.get_by_username_or_email(username, self.tenant_id)

        if not user:
            logger.warning(f"Authentication failed: user not found '{username}'")
            raise AuthenticationError("Invalid username or password")

        if not cast(bool, user.is_active):
            logger.warning(f"Authentication failed: user inactive '{user.id}'")
            raise AuthenticationError("Account is disabled")

        if not self._verify_password(password, cast(str, user.hashed_password)):
            logger.warning(f"Authentication failed: invalid password for user '{user.id}'")
            raise AuthenticationError("Invalid username or password")

        await self.user_repo.update_last_login(user.id, self.tenant_id)
        return user

    async def create_session(
        self,
        user: User,
        device_name: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Dict[str, Any]:
        stmt = (
            select(SovereignEntity.tenant_id)
            .join(EntityRepresentative, EntityRepresentative.entity_id == SovereignEntity.id)
            .where(EntityRepresentative.user_id == user.id)
            .where(EntityRepresentative.is_active == True)
            .limit(1)
        )
        result = await self.db.execute(stmt)
        active_tenant_id = result.scalar_one_or_none()

        if active_tenant_id != self.tenant_id:
            raise PermissionDeniedError("تعارض في المستأجر")

        access_token = jwt_service.create_access_token(
            user_id=cast(int, user.id),
            role=cast(str, user.system_role),
            session_version=cast(int, user.session_version),
            tenant_id=self.tenant_id
        )

        refresh_token, expires_at = jwt_service.create_refresh_token(
            user_id=cast(int, user.id),
            session_version=cast(int, user.session_version),
            tenant_id=self.tenant_id
        )

        await self.repo.create_refresh_token(
            user_id=cast(int, user.id),
            tenant_id=self.tenant_id,
            token=refresh_token,
            expires_at=expires_at,
            device_name=device_name,
            ip_address=ip_address,
            user_agent=user_agent
        )

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "Bearer",
            "expires_in": jwt_service.access_token_expire_minutes * 60,
            "user": {
                "id": cast(int, user.id),
                "username": cast(str, user.username),
                "email": cast(str, user.email),
                "role": cast(str, user.system_role),
                "sovereign_rank": cast(str, user.sovereign_rank),
                "tenant_id": active_tenant_id,
            }
        }

    async def refresh_access_token(self, refresh_token: str) -> Dict[str, Any]:
        payload = jwt_service.verify_token(refresh_token)
        if not payload:
            raise AuthenticationError("Invalid or expired refresh token")

        if payload.get("typ") != "refresh":
            raise AuthenticationError("Invalid token type")

        sub = payload.get("sub")
        if sub is None:
            raise AuthenticationError("Invalid token payload: missing 'sub'")
        user_id = int(sub)

        token_session_version = payload.get("sv")
        token_tenant_id = payload.get("tenant_id")

        if token_tenant_id != self.tenant_id:
            logger.warning(f"Tenant mismatch in refresh token: token={token_tenant_id}, request={self.tenant_id}")
            raise AuthenticationError("Tenant mismatch")

        user = await self.user_repo.get_by_id(user_id, self.tenant_id)

        if not user or not cast(bool, user.is_active):
            raise AuthenticationError("User not found or inactive")

        if cast(int, user.session_version) != token_session_version:
            await redis_client.delete(f"user:{user_id}:{self.tenant_id}")
            raise AuthenticationError("Session has been revoked")

        stored_token = await self.repo.get_refresh_token(refresh_token, self.tenant_id)
        if not stored_token:
            raise AuthenticationError("Refresh token not found")
        if stored_token.is_expired():
            raise AuthenticationError("Refresh token expired")
        if cast(bool, stored_token.revoked):
            raise AuthenticationError("Refresh token revoked")

        await self.repo.revoke_refresh_token(refresh_token, self.tenant_id)

        new_access_token = jwt_service.create_access_token(
            user_id=cast(int, user.id),
            role=cast(str, user.system_role),
            session_version=cast(int, user.session_version),
            tenant_id=self.tenant_id
        )

        new_refresh_token, expires_at = jwt_service.create_refresh_token(
            user_id=cast(int, user.id),
            session_version=cast(int, user.session_version),
            tenant_id=self.tenant_id
        )

        await self.repo.create_refresh_token(
            user_id=cast(int, user.id),
            tenant_id=self.tenant_id,
            token=new_refresh_token,
            expires_at=expires_at,
            device_name=cast(str, stored_token.device_name) if stored_token.device_name is not None else None,
            ip_address=cast(str, stored_token.ip_address) if stored_token.ip_address is not None else None,
            user_agent=cast(str, stored_token.user_agent) if stored_token.user_agent is not None else None,
        )

        return {
            "access_token": new_access_token,
            "refresh_token": new_refresh_token,
            "token_type": "Bearer",
            "expires_in": jwt_service.access_token_expire_minutes * 60,
        }

    async def revoke_session(self, user_id: int, refresh_token: str) -> bool:
        stored_token = await self.repo.get_refresh_token(refresh_token, self.tenant_id)
        if not stored_token or stored_token.user_id != user_id:
            return False
        if cast(bool, stored_token.revoked) or stored_token.is_expired():
            return False

        await self.repo.revoke_refresh_token(refresh_token, self.tenant_id)
        return True

    async def revoke_all_sessions(self, user_id: int) -> int:
        revoked_count = await self.repo.revoke_all_user_tokens(user_id, self.tenant_id)
        await self.repo.increment_session_version(user_id, self.tenant_id)
        await redis_client.delete(f"user:{user_id}:{self.tenant_id}")
        logger.info(f"All sessions revoked for user {user_id}, tenant {self.tenant_id}, cache deleted")
        return revoked_count

    async def get_active_sessions(
        self,
        user_id: int,
        skip: int = 0,
        limit: int = 20
    ) -> List[RefreshToken]:
        return await self.repo.list_user_refresh_tokens(
            user_id=user_id,
            tenant_id=self.tenant_id,
            skip=skip,
            limit=limit,
            include_revoked=False
        )

    def _verify_password(self, plain_password: str, hashed_password: str) -> bool:
        return pwd_context.verify(plain_password, hashed_password)

    def _hash_password(self, password: str) -> str:
        return pwd_context.hash(password)