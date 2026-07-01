# app/domains/identity/repository.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func, or_
from sqlalchemy.orm import selectinload
from typing import Optional
from app.domains.identity.models import User, Wallet
from app.core.errors import NotFoundError

class UserRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, user_id: int, load_wallet: bool = False) -> Optional[User]:
        """جلب المستخدم مع خيار جلب المحفظة"""
        query = select(User).where(User.id == user_id)
        if load_wallet:
            query = query.options(selectinload(User.wallet))
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_by_username_or_email(self, login: str) -> Optional[User]:
        """
        ✅ البحث عن المستخدم باستخدام func.lower() لتجنب حساسية حالة الأحرف.
        ✅ استخدام ILIKE لزيادة المرونة (لكننا نفضل القيمة الدقيقة مع تجاهل الحالة).
        """
        result = await self.db.execute(
            select(User).where(
                or_(
                    func.lower(User.email) == func.lower(login),
                    func.lower(User.username) == func.lower(login)
                )
            )
        )
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> Optional[User]:
        result = await self.db.execute(
            select(User).where(func.lower(User.email) == func.lower(email))
        )
        return result.scalar_one_or_none()

    async def get_by_username(self, username: str) -> Optional[User]:
        result = await self.db.execute(
            select(User).where(func.lower(User.username) == func.lower(username))
        )
        return result.scalar_one_or_none()

    async def create(self, user: User) -> User:
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def update(self, user_id: int, **kwargs) -> User:
        await self.db.execute(update(User).where(User.id == user_id).values(**kwargs))
        await self.db.commit()
        user = await self.get_by_id(user_id, load_wallet=True)
        if not user:
            raise NotFoundError("المستخدم غير موجود بعد التحديث")
        return user

    async def delete(self, user_id: int) -> None:
        await self.db.execute(update(User).where(User.id == user_id).values(is_active=False))
        await self.db.commit()


class WalletRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_user_id(self, user_id: int) -> Optional[Wallet]:
        result = await self.db.execute(select(Wallet).where(Wallet.user_id == user_id))
        return result.scalar_one_or_none()

    async def get_by_user_id_for_update(self, user_id: int) -> Optional[Wallet]:
        result = await self.db.execute(
            select(Wallet).where(Wallet.user_id == user_id).with_for_update()
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