# app/domains/auth/repository.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func, and_
from datetime import datetime, timezone
from typing import Optional, List, cast

from app.domains.auth.models import RefreshToken
from app.core.errors import NotFoundError

class AuthRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_refresh_token(
        self,
        user_id: int,
        tenant_id: int,
        token: str,
        expires_at: datetime,
        device_name: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> RefreshToken:
        token_hash = RefreshToken.hash_token(token)
        refresh_token = RefreshToken(
            user_id=user_id,
            tenant_id=tenant_id,
            token_hash=token_hash,
            expires_at=expires_at,
            device_name=device_name,
            ip_address=ip_address,
            user_agent=user_agent
        )
        self.db.add(refresh_token)
        await self.db.commit()
        await self.db.refresh(refresh_token)
        return refresh_token

    async def get_refresh_token(self, token: str, tenant_id: int) -> Optional[RefreshToken]:
        token_hash = RefreshToken.hash_token(token)
        result = await self.db.execute(
            select(RefreshToken).where(
                and_(
                    RefreshToken.token_hash == token_hash,
                    RefreshToken.tenant_id == tenant_id
                )
            )
        )
        return result.scalar_one_or_none()

    async def get_refresh_token_by_id(self, token_id: int, tenant_id: int) -> Optional[RefreshToken]:
        result = await self.db.execute(
            select(RefreshToken).where(
                and_(
                    RefreshToken.id == token_id,
                    RefreshToken.tenant_id == tenant_id
                )
            )
        )
        return result.scalar_one_or_none()

    async def list_user_refresh_tokens(
        self,
        user_id: int,
        tenant_id: int,
        skip: int = 0,
        limit: int = 20,
        include_revoked: bool = False
    ) -> List[RefreshToken]:
        query = select(RefreshToken).where(
            and_(
                RefreshToken.user_id == user_id,
                RefreshToken.tenant_id == tenant_id
            )
        )
        if not include_revoked:
             query = query.where(RefreshToken.revoked == False)  # type: ignore
        query = query.order_by(RefreshToken.created_at.desc())
        query = query.offset(skip).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def revoke_refresh_token(self, token: str, tenant_id: int) -> Optional[RefreshToken]:
        token_hash = RefreshToken.hash_token(token)
        result = await self.db.execute(
            select(RefreshToken).where(
                and_(
                    RefreshToken.token_hash == token_hash,
                    RefreshToken.tenant_id == tenant_id
                )
            )
        )
        refresh_token = result.scalar_one_or_none()
        if refresh_token and not cast(bool, refresh_token.revoked):
            refresh_token.revoke()
            await self.db.commit()
            await self.db.refresh(refresh_token)
        return refresh_token

    async def revoke_all_user_tokens(self, user_id: int, tenant_id: int) -> int:
        result = await self.db.execute(
            update(RefreshToken)
            .where(
                and_(
                    RefreshToken.user_id == user_id,
                    RefreshToken.tenant_id == tenant_id,
                            RefreshToken.revoked == False  # type: ignore
                )
            )
            .values(revoked=True, revoked_at=datetime.now(timezone.utc))
            .returning(RefreshToken.id)
        )
        await self.db.commit()
        return len(result.scalars().all())

    async def delete_expired_tokens(self, tenant_id: int) -> int:
        result = await self.db.execute(
            delete(RefreshToken).where(
                and_(
                    RefreshToken.tenant_id == tenant_id,
                    RefreshToken.expires_at < datetime.now(timezone.utc)
                )
            )
        )
        await self.db.commit()
        return result.rowcount

    async def increment_session_version(self, user_id: int, tenant_id: int) -> int:
        from app.domains.identity.models import User
        result = await self.db.execute(
            update(User)
            .where(and_(User.id == user_id, User.tenant_id == tenant_id))
            .values(session_version=User.session_version + 1)
            .returning(User.session_version)
        )
        await self.db.commit()
        new_version = result.scalar()
        return new_version or 0