# app/domains/identity/repository.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func, or_, and_
from sqlalchemy.orm import selectinload
from typing import Optional, cast
from app.domains.identity.models import User
from app.domains.finance.models import Wallet
from app.core.errors import NotFoundError
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