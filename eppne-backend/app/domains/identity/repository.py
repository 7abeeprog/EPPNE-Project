# app/domains/identity/repository.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func, or_
from sqlalchemy.orm import selectinload
from typing import Optional, cast
from app.domains.identity.models import User, IdentityWallet as Wallet
from app.core.errors import NotFoundError
from datetime import datetime, timezone


class UserRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, user_id: int, load_wallet: bool = False) -> Optional[User]:
        query = select(User).where(User.id == user_id)  # type: ignore
        if load_wallet:
            query = query.options(selectinload(User.wallet))
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_by_username_or_email(self, login: str) -> Optional[User]:
        result = await self.db.execute(
            select(User).where(
                or_(
                    func.lower(User.email) == func.lower(login),  # type: ignore
                    func.lower(User.username) == func.lower(login)  # type: ignore
                )
            )
        )
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> Optional[User]:
        result = await self.db.execute(
            select(User).where(func.lower(User.email) == func.lower(email))  # type: ignore
        )
        return result.scalar_one_or_none()

    async def get_by_username(self, username: str) -> Optional[User]:
        result = await self.db.execute(
            select(User).where(func.lower(User.username) == func.lower(username))  # type: ignore
        )
        return result.scalar_one_or_none()

    async def get_by_idempotency_key(self, key: str) -> Optional[User]:
        result = await self.db.execute(select(User).where(User.idempotency_key == key))  # type: ignore
        return result.scalar_one_or_none()

    async def create(self, user: User) -> User:
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def update(self, user_id: int, **kwargs) -> User:
        await self.db.execute(update(User).where(User.id == user_id).values(**kwargs))  # type: ignore
        await self.db.commit()
        user = await self.get_by_id(user_id, load_wallet=True)
        if not user:
            raise NotFoundError("المستخدم غير موجود بعد التحديث")
        return user

    async def delete(self, user_id: int) -> None:
        await self.db.execute(update(User).where(User.id == user_id).values(is_active=False))  # type: ignore
        await self.db.commit()

    async def update_last_login(self, user_or_id) -> None:
        user_id = user_or_id.id if hasattr(user_or_id, "id") else user_or_id
        await self.db.execute(
            update(User)
            .where(User.id == user_id)  # type: ignore
            .values(last_login_at=datetime.now(timezone.utc))  # type: ignore
        )
        await self.db.commit()


class WalletRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_user_id(self, user_id: int) -> Optional[Wallet]:
        result = await self.db.execute(select(Wallet).where(Wallet.user_id == user_id))  # type: ignore
        return result.scalar_one_or_none()

    async def get_by_user_id_for_update(self, user_id: int) -> Optional[Wallet]:
        result = await self.db.execute(
            select(Wallet).where(Wallet.user_id == user_id).with_for_update()  # type: ignore
        )
        return result.scalar_one_or_none()

    async def create(self, user_id: int, wallet_address: Optional[str] = None) -> Wallet:
        wallet = Wallet(user_id=user_id, wallet_address=wallet_address)
        self.db.add(wallet)
        await self.db.commit()
        await self.db.refresh(wallet)
        return wallet

    async def update_balances(self, wallet_id: int, new_balances: dict) -> Wallet:
        await self.db.execute(
            update(Wallet).where(Wallet.id == wallet_id).values(balances=new_balances)  # type: ignore
        )
        await self.db.commit()
        result = await self.db.execute(select(Wallet).where(Wallet.id == wallet_id))  # type: ignore
        wallet = result.scalar_one_or_none()
        if not wallet:
            raise NotFoundError("المحفظة غير موجودة")
        return wallet

    async def freeze(self, wallet_id: int) -> Wallet:
        await self.db.execute(
            update(Wallet).where(Wallet.id == wallet_id).values(is_frozen=True)  # type: ignore
        )
        await self.db.commit()
        result = await self.db.execute(select(Wallet).where(Wallet.id == wallet_id))  # type: ignore
        return result.scalar_one_or_none()