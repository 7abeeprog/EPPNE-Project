# app/domains/finance/repository.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func, or_
from sqlalchemy.orm import load_only
from datetime import datetime

from app.domains.finance.models import Wallet, Transaction, SystemState, AuditLog
from app.core.errors import NotFoundError
from app.core.pagination import PaginatedResponse

class WalletRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_user_id(self, user_id: int) -> Wallet | None:
        result = await self.db.execute(select(Wallet).where(Wallet.user_id == user_id))
        return result.scalar_one_or_none()

    async def get_by_user_id_for_update(self, user_id: int) -> Wallet | None:
        """قفل السجل عند التحديث لتجنب سباق العمليات (Race Conditions)"""
        result = await self.db.execute(
            select(Wallet).where(Wallet.user_id == user_id).with_for_update()
        )
        return result.scalar_one_or_none()

    async def create(self, user_id: int, wallet_address: str = None) -> Wallet:
        wallet = Wallet(user_id=user_id, wallet_address=wallet_address, balances={
            "MR_POUND": 0, "MR_USDT": 0, "MR7": 0, "NBT": 0, "MRX": 0
        })
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


class TransactionRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, **kwargs) -> Transaction:
        tx = Transaction(**kwargs)
        self.db.add(tx)
        await self.db.commit()
        await self.db.refresh(tx)
        return tx

    async def get_by_idempotency_key(self, idempotency_key: str) -> Transaction | None:
        """البحث عن معاملة بواسطة مفتاح عدم التكرار"""
        if not idempotency_key:
            return None
        result = await self.db.execute(
            select(Transaction).where(Transaction.idempotency_key == idempotency_key)
        )
        return result.scalar_one_or_none()

    async def get_by_user_paginated(
        self,
        user_id: int,
        skip: int = 0,
        limit: int = 20
    ) -> PaginatedResponse[Transaction]:
        """جلب المعاملات مع Pagination حقيقي وتحسين الأداء باستخدام load_only"""
        
        # Base Query
        query = (
            select(Transaction)
            .where(
                or_(
                    Transaction.sender_id == user_id,
                    Transaction.receiver_id == user_id
                )
            )
            .options(
                load_only(
                    Transaction.id, Transaction.tx_hash, Transaction.amount, 
                    Transaction.currency, Transaction.tx_type, Transaction.status,
                    Transaction.notes, Transaction.created_at,
                    Transaction.sender_id, Transaction.receiver_id
                )
            )
            .order_by(Transaction.created_at.desc())
        )

        # حساب العدد الإجمالي
        count_query = select(func.count()).select_from(query.subquery())
        count_result = await self.db.execute(count_query)
        total = count_result.scalar() or 0

        # تطبيق Pagination
        paginated_query = query.offset(skip).limit(limit)
        result = await self.db.execute(paginated_query)
        items = result.scalars().all()

        return PaginatedResponse(
            data=items,
            total=total,
            skip=skip,
            limit=limit
        )


class SystemStateRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_state(self) -> SystemState:
        result = await self.db.execute(select(SystemState).order_by(SystemState.id.desc()).limit(1))
        state = result.scalar_one_or_none()
        if not state:
            state = SystemState()
            self.db.add(state)
            await self.db.commit()
            await self.db.refresh(state)
        return state

    async def update_crypto_mode(self, mode: str, updated_by_id: int) -> SystemState:
        state = await self.get_state()
        state.crypto_mode = mode
        state.updated_by_id = updated_by_id
        await self.db.commit()
        await self.db.refresh(state)
        return state

    async def update_exchange_rates(self, rates: dict, updated_by_id: int) -> SystemState:
        state = await self.get_state()
        state.exchange_rates = rates
        state.updated_by_id = updated_by_id
        await self.db.commit()
        await self.db.refresh(state)
        return state
    
    async def update_max_supply(self, max_supply: dict, updated_by_id: int) -> SystemState:
        state = await self.get_state()
        state.max_supply = max_supply
        state.updated_by_id = updated_by_id
        await self.db.commit()
        await self.db.refresh(state)
        return state


class AuditLogRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, user_id: int, action: str, details: dict, ip_address: str = None, user_agent: str = None) -> AuditLog:
        log = AuditLog(
            user_id=user_id,
            action=action,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent
        )
        self.db.add(log)
        await self.db.commit()
        await self.db.refresh(log)
        return log