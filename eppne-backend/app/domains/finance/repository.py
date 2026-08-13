# app/domains/finance/repository.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func, or_, and_
from sqlalchemy.orm import load_only
from datetime import datetime
from typing import Optional, List, cast

from app.domains.finance.models import Wallet, Transaction, SystemState, AuditLog
from app.domains.identity.models import User
from app.core.errors import NotFoundError
from app.domains.finance.schemas import TransactionResponse


class WalletRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_user_id(self, user_id: int, tenant_id: int) -> Optional[Wallet]:
        result = await self.db.execute(
            select(Wallet).where(
                and_(Wallet.user_id == user_id, Wallet.tenant_id == tenant_id)
            )
        )
        return result.scalar_one_or_none()

    async def get_by_user_id_for_update(self, user_id: int, tenant_id: int) -> Optional[Wallet]:
        result = await self.db.execute(
            select(Wallet)
            .where(and_(Wallet.user_id == user_id, Wallet.tenant_id == tenant_id))
            .with_for_update()
        )
        return result.scalar_one_or_none()

    async def create(self, user_id: int, tenant_id: int, wallet_address: Optional[str] = None) -> Wallet:
        wallet = Wallet(
            user_id=user_id,
            tenant_id=tenant_id,
            wallet_address=wallet_address,
            balances={
                "MR_POUND": 0, "MR_USDT": 0, "MR7": 0, "NBT": 0, "MRX": 0
            }
        )
        self.db.add(wallet)
        await self.db.flush()
        await self.db.refresh(wallet)
        return wallet

    async def update_balances(self, wallet_id: int, new_balances: dict) -> Wallet:
        await self.db.execute(
            update(Wallet).where(Wallet.id == wallet_id).values(balances=new_balances)
        )
        await self.db.flush()
        result = await self.db.execute(select(Wallet).where(Wallet.id == wallet_id))
        wallet = result.scalar_one_or_none()
        if not wallet:
            raise NotFoundError("المحفظة غير موجودة")
        return wallet

    async def freeze(self, wallet_id: int, tenant_id: int) -> Wallet:
        await self.db.execute(
            update(Wallet)
            .where(and_(Wallet.id == wallet_id, Wallet.tenant_id == tenant_id))
            .values(is_frozen=True)
        )
        await self.db.commit()
        result = await self.db.execute(select(Wallet).where(Wallet.id == wallet_id))
        return result.scalar_one_or_none()


class TransactionRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, **kwargs) -> Transaction:
        tx = Transaction(**kwargs)
        self.db.add(tx)
        await self.db.flush()
        await self.db.refresh(tx)
        return tx

    async def get_by_idempotency_key(self, idempotency_key: str, tenant_id: int) -> Optional[Transaction]:
        if not idempotency_key:
            return None
        result = await self.db.execute(
            select(Transaction)
            .join(User, or_(User.id == Transaction.sender_id, User.id == Transaction.receiver_id))
            .where(
                and_(
                    Transaction.idempotency_key == idempotency_key,
                    User.tenant_id == tenant_id
                )
            )
        )
        return result.scalar_one_or_none()

    async def get_by_user_paginated(
        self,
        user_id: int,
        tenant_id: int,
        skip: int = 0,
        limit: int = 20,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        currency: Optional[str] = None,
        tx_type: Optional[str] = None
    ):
        query = (
            select(Transaction)
            .join(User, or_(User.id == Transaction.sender_id, User.id == Transaction.receiver_id))
            .where(
                and_(
                    or_(
                        Transaction.sender_id == user_id,
                        Transaction.receiver_id == user_id
                    ),
                    User.tenant_id == tenant_id
                )
            )
            .options(
                load_only(  # type: ignore
                    "id", "tx_hash", "amount",
                    "currency", "tx_type", "status",
                    "notes", "created_at",
                    "sender_id", "receiver_id"
                )
            )
        )

        if start_date:
            query = query.where(Transaction.created_at >= start_date)
        if end_date:
            query = query.where(Transaction.created_at <= end_date)
        if currency:
            query = query.where(Transaction.currency == currency)
        if tx_type:
            query = query.where(Transaction.tx_type == tx_type)

        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0

        query = query.order_by(Transaction.created_at.desc())
        paginated_query = query.offset(skip).limit(limit)
        result = await self.db.execute(paginated_query)
        items = result.scalars().all()

        schema_items = [TransactionResponse.model_validate(item) for item in items]

        return {
            "items": schema_items,
            "total": total,
            "skip": skip,
            "limit": limit
        }

    async def count_by_user(
        self,
        user_id: int,
        tenant_id: int,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        currency: Optional[str] = None,
        tx_type: Optional[str] = None
    ) -> int:
        query = (
            select(func.count())
            .select_from(Transaction)
            .join(User, or_(User.id == Transaction.sender_id, User.id == Transaction.receiver_id))
            .where(
                and_(
                    or_(
                        Transaction.sender_id == user_id,
                        Transaction.receiver_id == user_id
                    ),
                    User.tenant_id == tenant_id
                )
            )
        )

        if start_date:
            query = query.where(Transaction.created_at >= start_date)
        if end_date:
            query = query.where(Transaction.created_at <= end_date)
        if currency:
            query = query.where(Transaction.currency == currency)
        if tx_type:
            query = query.where(Transaction.tx_type == tx_type)

        result = await self.db.execute(query)
        return result.scalar() or 0


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
        setattr(state, "crypto_mode", mode)
        setattr(state, "updated_by_id", updated_by_id)
        await self.db.commit()
        await self.db.refresh(state)
        return state

    async def update_exchange_rates(self, rates: dict, updated_by_id: int) -> SystemState:
        state = await self.get_state()
        setattr(state, "exchange_rates", rates)
        setattr(state, "updated_by_id", updated_by_id)
        await self.db.commit()
        await self.db.refresh(state)
        return state

    async def update_max_supply(self, max_supply: dict, updated_by_id: int) -> SystemState:
        state = await self.get_state()
        setattr(state, "max_supply", max_supply)
        setattr(state, "updated_by_id", updated_by_id)
        await self.db.commit()
        await self.db.refresh(state)
        return state


class AuditLogRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        user_id: int,
        tenant_id: int,
        action: str,
        details: dict,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> AuditLog:
        log = AuditLog(
            user_id=user_id,
            tenant_id=tenant_id,
            action=action,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent
        )
        self.db.add(log)
        await self.db.flush()
        await self.db.refresh(log)
        return log