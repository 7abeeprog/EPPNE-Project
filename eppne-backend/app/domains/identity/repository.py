# app/domains/identity/repository.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func, or_, and_
from sqlalchemy.orm import selectinload
from typing import Optional, List, cast
from app.domains.identity.models import User, RefreshToken, TenantInvitation
from app.domains.finance.models import Wallet
from app.core.errors import NotFoundError
from app.core.enums import InvitationStatus
from datetime import datetime, timezone

class UserRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    def _apply_tenant_filter(self, query, tenant_id: int):
        if tenant_id is not None:
            return query.where(User.tenant_id == tenant_id)
        return query

    async def get_by_id(self, user_id: int, tenant_id: int, load_wallet: bool = False) -> Optional[User]:
        query = select(User).where(and_(User.id == user_id, User.tenant_id == tenant_id))
        if load_wallet:
            query = query.options(selectinload(User.wallet))
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_by_username_or_email(self, login: str, tenant_id: int) -> Optional[User]:
        query = select(User).where(
            and_(
                or_(
                    func.lower(User.email) == func.lower(login),
                    func.lower(User.username) == func.lower(login)
                ),
                User.tenant_id == tenant_id
            )
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str, tenant_id: int) -> Optional[User]:
        query = select(User).where(and_(func.lower(User.email) == func.lower(email), User.tenant_id == tenant_id))
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_by_username(self, username: str, tenant_id: int) -> Optional[User]:
        query = select(User).where(and_(func.lower(User.username) == func.lower(username), User.tenant_id == tenant_id))
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_by_idempotency_key(self, key: str, tenant_id: int) -> Optional[User]:
        query = select(User).where(and_(User.idempotency_key == key, User.tenant_id == tenant_id))
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def create(self, user: User) -> User:
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def update(self, user_id: int, tenant_id: int, **kwargs) -> User:
        await self.db.execute(
            update(User)
            .where(and_(User.id == user_id, User.tenant_id == tenant_id))
            .values(**kwargs)
        )
        await self.db.commit()
        user = await self.get_by_id(user_id, tenant_id, load_wallet=True)
        if not user:
            raise NotFoundError("المستخدم غير موجود بعد التحديث")
        return user

    async def delete(self, user_id: int, tenant_id: int) -> None:
        await self.db.execute(
            update(User)
            .where(and_(User.id == user_id, User.tenant_id == tenant_id))
            .values(is_active=False)
        )
        await self.db.commit()

    async def update_last_login(self, user_or_id, tenant_id: int) -> None:
        user_id = user_or_id.id if hasattr(user_or_id, "id") else user_or_id
        await self.db.execute(
            update(User)
            .where(and_(User.id == user_id, User.tenant_id == tenant_id))
            .values(last_login_at=datetime.now(timezone.utc))
        )
        await self.db.commit()

    async def increment_session_version(self, user_id: int, tenant_id: int) -> None:
        await self.db.execute(
            update(User)
            .where(and_(User.id == user_id, User.tenant_id == tenant_id))
            .values(session_version=User.session_version + 1)
        )
        await self.db.commit()


class RefreshTokenRepository:
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


class WalletRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ✅ إضافة tenant_id كمعامل وتصفية
    async def get_by_user_id(self, user_id: int, tenant_id: int) -> Optional[Wallet]:
        result = await self.db.execute(
            select(Wallet).where(
                and_(Wallet.user_id == user_id, Wallet.tenant_id == tenant_id)
            )
        )
        return result.scalar_one_or_none()

    # ✅ إضافة tenant_id كمعامل وتصفية
    async def get_by_user_id_for_update(self, user_id: int, tenant_id: int) -> Optional[Wallet]:
        result = await self.db.execute(
            select(Wallet)
            .where(and_(Wallet.user_id == user_id, Wallet.tenant_id == tenant_id))
            .with_for_update()
        )
        return result.scalar_one_or_none()

    # ✅ إضافة tenant_id كمعامل وتخزينه عند الإنشاء
    async def create(self, user_id: int, tenant_id: int, wallet_address: Optional[str] = None) -> Wallet:
        wallet = Wallet(
            user_id=user_id,
            tenant_id=tenant_id,  # ✅ تعيين tenant_id
            wallet_address=wallet_address
        )
        self.db.add(wallet)
        await self.db.commit()
        await self.db.refresh(wallet)
        return wallet

    async def update_balances(self, wallet_id: int, new_balances: dict) -> Wallet:
        await self.db.execute(
            update(Wallet).where(Wallet.id == wallet_id).values(balances=new_balances)
        )
        await self.db.commit()
        result = await self.db.execute(select(Wallet).where(Wallet.id == wallet_id))
        wallet = result.scalar_one_or_none()
        if not wallet:
            raise NotFoundError("المحفظة غير موجودة")
        return wallet

    async def freeze(self, wallet_id: int) -> Wallet:
        await self.db.execute(
            update(Wallet).where(Wallet.id == wallet_id).values(is_frozen=True)
        )
        await self.db.commit()
        result = await self.db.execute(select(Wallet).where(Wallet.id == wallet_id))
        return result.scalar_one_or_none()


class InvitationRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        tenant_id: int,
        referrer_user_id: int,
        token: str,
        email: Optional[str] = None,
        product_id: Optional[int] = None,
        max_uses: Optional[int] = None,
        expires_at: Optional[datetime] = None,
    ) -> TenantInvitation:
        invitation = TenantInvitation(
            tenant_id=tenant_id,
            referrer_user_id=referrer_user_id,
            token_hash=TenantInvitation.hash_token(token),
            email=email,
            product_id=product_id,
            max_uses=max_uses,
            expires_at=expires_at,
        )
        self.db.add(invitation)
        await self.db.commit()
        await self.db.refresh(invitation)
        return invitation

    async def get_by_token(self, token: str) -> Optional[TenantInvitation]:
        token_hash = TenantInvitation.hash_token(token)
        result = await self.db.execute(
            select(TenantInvitation).where(TenantInvitation.token_hash == token_hash)
        )
        return result.scalar_one_or_none()

    async def get_by_id(self, invitation_id: int, tenant_id: int) -> Optional[TenantInvitation]:
        result = await self.db.execute(
            select(TenantInvitation).where(
                and_(TenantInvitation.id == invitation_id, TenantInvitation.tenant_id == tenant_id)
            )
        )
        return result.scalar_one_or_none()

    async def list_by_referrer(self, referrer_user_id: int, tenant_id: int, skip: int = 0, limit: int = 20) -> List[TenantInvitation]:
        query = select(TenantInvitation).where(
            and_(TenantInvitation.referrer_user_id == referrer_user_id, TenantInvitation.tenant_id == tenant_id)
        ).order_by(TenantInvitation.created_at.desc()).offset(skip).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def list_by_tenant(self, tenant_id: int, skip: int = 0, limit: int = 20) -> List[TenantInvitation]:
        query = select(TenantInvitation).where(
            TenantInvitation.tenant_id == tenant_id
        ).order_by(TenantInvitation.created_at.desc()).offset(skip).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def claim_use(self, invitation_id: int) -> bool:
        result = await self.db.execute(
            update(TenantInvitation)
            .where(
                TenantInvitation.id == invitation_id,
                TenantInvitation.status == InvitationStatus.PENDING,
                or_(TenantInvitation.max_uses.is_(None), TenantInvitation.current_uses < TenantInvitation.max_uses),
                or_(TenantInvitation.expires_at.is_(None), TenantInvitation.expires_at > func.now()),
            )
            .values(current_uses=TenantInvitation.current_uses + 1, accepted_at=func.now())
            .returning(TenantInvitation.id)
        )
        await self.db.commit()
        return result.scalar_one_or_none() is not None

    async def release_use(self, invitation_id: int) -> None:
        await self.db.execute(
            update(TenantInvitation).where(TenantInvitation.id == invitation_id)
            .values(current_uses=TenantInvitation.current_uses - 1)
        )
        await self.db.commit()

    async def finalize_if_exhausted(self, invitation_id: int) -> None:
        await self.db.execute(
            update(TenantInvitation)
            .where(
                TenantInvitation.id == invitation_id,
                TenantInvitation.max_uses.isnot(None),
                TenantInvitation.current_uses >= TenantInvitation.max_uses,
            )
            .values(status=InvitationStatus.ACCEPTED)
        )
        await self.db.commit()

    async def revoke(self, invitation_id: int, tenant_id: int, revoked_by_user_id: int) -> Optional[TenantInvitation]:
        result = await self.db.execute(
            select(TenantInvitation).where(
                and_(TenantInvitation.id == invitation_id, TenantInvitation.tenant_id == tenant_id)
            )
        )
        invitation = result.scalar_one_or_none()
        if not invitation:
            return None
        invitation.status = InvitationStatus.REVOKED
        invitation.revoked_by_user_id = revoked_by_user_id
        invitation.revoked_at = datetime.now(timezone.utc)
        await self.db.commit()
        await self.db.refresh(invitation)
        return invitation