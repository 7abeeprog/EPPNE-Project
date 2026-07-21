# app/domains/finance/service.py
from sqlalchemy.ext.asyncio import AsyncSession
from decimal import Decimal
import uuid
from datetime import datetime, timezone
from typing import Optional, cast

from app.domains.finance.repository import WalletRepository, TransactionRepository, SystemStateRepository
from app.domains.finance.models import Wallet, AuditLog
from app.domains.finance.schemas import PaginatedTransactionResponse, TransactionResponse
from app.core.errors import InsufficientBalanceError, PermissionDeniedError, NotFoundError, ValidationError
from app.core.logging_conf import logger
from app.core.event_bus import EventBus
from app.domains.identity.models import User


class FinanceService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.wallet_repo = WalletRepository(db)
        self.tx_repo = TransactionRepository(db)
        self.state_repo = SystemStateRepository(db)
        self.event_bus = EventBus()

    async def get_or_create_wallet(self, user_id: int) -> Wallet:
        wallet = await self.wallet_repo.get_by_user_id(user_id)
        if not wallet:
            wallet = await self.wallet_repo.create(user_id)
        return wallet

    async def get_or_create_wallet_for_update(self, user_id: int) -> Wallet:
        wallet = await self.wallet_repo.get_by_user_id_for_update(user_id)
        if not wallet:
            wallet = await self.wallet_repo.create(user_id)
            wallet = await self.wallet_repo.get_by_user_id_for_update(user_id)
        return wallet

    async def _create_audit_log(self, user_id: int, action: str, details: dict, ip: Optional[str] = None, ua: Optional[str] = None):
        log = AuditLog(
            user_id=user_id,
            action=action,
            details=details,
            ip_address=ip,
            user_agent=ua,
        )
        self.db.add(log)
        await self.db.commit()

    async def get_balances(self, user_id: int, hide_crypto: bool = False) -> dict:
        wallet = await self.get_or_create_wallet(user_id)
        balances = getattr(wallet, "balances", {})  # type: ignore
        if hide_crypto:
            return {"LOYALTY_POINTS": sum(balances.values())}
        return balances

    async def transfer(
        self,
        sender_id: int,
        receiver_email: str,
        currency: str,
        amount: Decimal,
        idempotency_key: str,
        notes: Optional[str] = None,
        ip: Optional[str] = None,
        ua: Optional[str] = None
    ):
        if not idempotency_key:
            raise ValidationError("Idempotency key is required")

        existing_tx = await self.tx_repo.get_by_idempotency_key(idempotency_key)
        if existing_tx:
            logger.warning(f"Duplicate transfer request detected: {idempotency_key}")
            return existing_tx

        from app.domains.identity.repository import UserRepository
        user_repo = UserRepository(self.db)
        receiver = await user_repo.get_by_email(receiver_email)
        if not receiver:
            raise NotFoundError("المستلم غير موجود")

        state = await self.state_repo.get_state()
        crypto_mode = str(getattr(state, "crypto_mode", "FULL_CRYPTO"))  # type: ignore
        if crypto_mode == "POINTS_ONLY" and currency != "LOYALTY_POINTS":
            raise PermissionDeniedError("العملات المشفرة معطلة حالياً")

        async with self.db.begin_nested():
            # استخدام cast لتأكيد الأنواع وإسكات Pylance نهائياً
            first_id, second_id = sorted([sender_id, cast(int, receiver.id)])
            first_wallet = await self.get_or_create_wallet_for_update(first_id)
            second_wallet = await self.get_or_create_wallet_for_update(second_id)

            sender_wallet = first_wallet if first_id == sender_id else second_wallet
            receiver_wallet = second_wallet if second_id == receiver.id else first_wallet

            sender_frozen = cast(bool, getattr(sender_wallet, "is_frozen", False))
            receiver_frozen = cast(bool, getattr(receiver_wallet, "is_frozen", False))
            
            if sender_frozen:
                raise PermissionDeniedError("محفظتك مجمدة. يرجى التواصل مع الدعم.")
            if receiver_frozen:
                raise PermissionDeniedError("محفظة المستلم مجمدة.")

            sender_balances = getattr(sender_wallet, "balances", {}).copy()  # type: ignore
            sender_current = Decimal(str(sender_balances.get(currency, 0)))
            if sender_current < amount:
                raise InsufficientBalanceError(f"رصيد غير كافٍ من {currency}")

            sender_balances[currency] = float(sender_current - amount)  # type: ignore
            receiver_balances = getattr(receiver_wallet, "balances", {}).copy()  # type: ignore
            receiver_balances[currency] = receiver_balances.get(currency, 0) + float(amount)  # type: ignore

            await self.wallet_repo.update_balances(sender_wallet.id, sender_balances)  # type: ignore
            await self.wallet_repo.update_balances(receiver_wallet.id, receiver_balances)  # type: ignore

            tx_hash = f"TX-{uuid.uuid4().hex[:12].upper()}"
            tx = await self.tx_repo.create(
                tx_hash=tx_hash,
                idempotency_key=idempotency_key,
                sender_id=sender_id,
                receiver_id=receiver.id,  # type: ignore
                from_wallet_id=sender_wallet.id,  # type: ignore
                to_wallet_id=receiver_wallet.id,  # type: ignore
                amount=float(amount),
                currency=currency,
                tx_type="TRANSFER",
                status="COMPLETED",
                notes=notes,
            )

        await self._create_audit_log(
            user_id=sender_id,
            action="TRANSFER",
            details={
                "receiver_id": receiver.id,  # type: ignore
                "receiver_email": receiver_email,
                "currency": currency,
                "amount": float(amount),
                "tx_hash": tx_hash,
            },
            ip=ip,
            ua=ua,
        )

        return tx

    async def swap(
        self,
        user_id: int,
        from_currency: str,
        to_currency: str,
        amount_in: Decimal,
        idempotency_key: str,
        ip: Optional[str] = None,
        ua: Optional[str] = None
    ):
        if from_currency == to_currency:
            raise ValidationError("لا يمكن تحويل العملة لنفسها")

        if not idempotency_key:
            raise ValidationError("Idempotency key is required")

        existing_tx = await self.tx_repo.get_by_idempotency_key(idempotency_key)
        if existing_tx:
            logger.warning(f"Duplicate swap request detected: {idempotency_key}")
            return existing_tx

        state = await self.state_repo.get_state()
        crypto_mode = str(getattr(state, "crypto_mode", "FULL_CRYPTO"))  # type: ignore
        if crypto_mode == "POINTS_ONLY":
            raise PermissionDeniedError("خدمة الصرافة معطلة في وضع النقاط فقط")

        rates = getattr(state, "exchange_rates", {}).copy()  # type: ignore
        if from_currency not in rates or to_currency not in rates:
            raise ValidationError("عملة غير مدعومة")

        value_in_base = float(amount_in) * rates[from_currency]  # type: ignore
        amount_out = Decimal(value_in_base / rates[to_currency])  # type: ignore

        async with self.db.begin_nested():
            wallet = await self.get_or_create_wallet_for_update(user_id)

            wallet_frozen = bool(getattr(wallet, "is_frozen", False))  # type: ignore
            if wallet_frozen:  # type: ignore
                raise PermissionDeniedError("محفظتك مجمدة")

            balances = getattr(wallet, "balances", {}).copy()  # type: ignore
            current_from = Decimal(str(balances.get(from_currency, 0)))
            if current_from < amount_in:
                raise InsufficientBalanceError(f"رصيد غير كافٍ من {from_currency}")

            balances[from_currency] = float(current_from - amount_in)  # type: ignore
            balances[to_currency] = balances.get(to_currency, 0) + float(amount_out)  # type: ignore
            await self.wallet_repo.update_balances(wallet.id, balances)  # type: ignore

            tx_hash_out = f"SWAP-OUT-{uuid.uuid4().hex[:12].upper()}"
            tx_hash_in = f"SWAP-IN-{uuid.uuid4().hex[:12].upper()}"

            await self.tx_repo.create(
                tx_hash=tx_hash_out,
                idempotency_key=f"{idempotency_key}-out",
                sender_id=user_id,
                from_wallet_id=wallet.id,  # type: ignore
                amount=float(amount_in),
                currency=from_currency,
                exchange_rate_applied=rates[from_currency] / rates[to_currency],  # type: ignore
                tx_type="SWAP_OUT",
                status="COMPLETED",
            )
            await self.tx_repo.create(
                tx_hash=tx_hash_in,
                idempotency_key=f"{idempotency_key}-in",
                receiver_id=user_id,
                to_wallet_id=wallet.id,  # type: ignore
                amount=float(amount_out),
                currency=to_currency,
                exchange_rate_applied=rates[to_currency] / rates[from_currency],  # type: ignore
                tx_type="SWAP_IN",
                status="COMPLETED",
            )

        await self._create_audit_log(
            user_id=user_id,
            action="SWAP",
            details={
                "from_currency": from_currency,
                "from_amount": float(amount_in),
                "to_currency": to_currency,
                "to_amount": float(amount_out),
                "rate": rates[to_currency] / rates[from_currency],  # type: ignore
            },
            ip=ip,
            ua=ua,
        )

        return {
            "from_amount": float(amount_in),
            "from_currency": from_currency,
            "to_amount": float(amount_out),
            "to_currency": to_currency,
            "rate_applied": rates[to_currency] / rates[from_currency],  # type: ignore
            "tx_hash": tx_hash_in
        }

    async def mint_currency(
        self,
        admin_id: int,
        currency: str,
        amount: Decimal,
        idempotency_key: str,
        ip: Optional[str] = None,
        ua: Optional[str] = None
    ):
        if not idempotency_key:
            raise ValidationError("Idempotency key is required")

        existing_tx = await self.tx_repo.get_by_idempotency_key(idempotency_key)
        if existing_tx:
            logger.warning(f"Duplicate mint request detected: {idempotency_key}")
            return existing_tx

        state = await self.state_repo.get_state()
        current_supply = getattr(state, "total_supply", {}).get(currency, 0)  # type: ignore
        max_supply = getattr(state, "max_supply", {}).get(currency, 0)  # type: ignore

        if current_supply + float(amount) > max_supply:  # type: ignore
            raise ValidationError(f"لا يمكن سك {currency}: سيتم تجاوز الحد الأقصى ({max_supply})")

        async with self.db.begin_nested():
            wallet = await self.get_or_create_wallet_for_update(admin_id)
            balances = getattr(wallet, "balances", {}).copy()  # type: ignore
            balances[currency] = balances.get(currency, 0) + float(amount)  # type: ignore
            await self.wallet_repo.update_balances(wallet.id, balances)  # type: ignore

            new_total = current_supply + float(amount)  # type: ignore
            setattr(state, "total_supply", {**getattr(state, "total_supply", {}), currency: new_total})  # type: ignore
            setattr(state, "updated_by_id", admin_id)  # type: ignore
            await self.db.commit()

            tx_hash = f"MINT-{uuid.uuid4().hex[:12].upper()}"
            tx = await self.tx_repo.create(
                tx_hash=tx_hash,
                idempotency_key=idempotency_key,
                receiver_id=admin_id,
                to_wallet_id=wallet.id,  # type: ignore
                amount=float(amount),
                currency=currency,
                tx_type="MINT",
                status="COMPLETED",
                notes=f"سك عملات سيادية من البنك المركزي. العرض الجديد: {new_total}",
            )

        await self._create_audit_log(
            user_id=admin_id,
            action="MINT",
            details={
                "currency": currency,
                "amount": float(amount),
                "new_total_supply": new_total,
                "tx_hash": tx_hash,
            },
            ip=ip,
            ua=ua,
        )

        return tx

    async def get_transaction_history(
        self,
        user_id: int,
        skip: int = 0,
        limit: int = 20,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        currency: Optional[str] = None,
        tx_type: Optional[str] = None
    ) -> PaginatedTransactionResponse:
        start = datetime.fromisoformat(start_date) if start_date else None
        end = datetime.fromisoformat(end_date) if end_date else None

        items = await self.tx_repo.get_by_user_paginated(
            user_id=user_id,
            skip=skip,
            limit=limit,
            start_date=start,
            end_date=end,
            currency=currency,
            tx_type=tx_type
        )

        total = await self.tx_repo.count_by_user(
            user_id=user_id,
            start_date=start,
            end_date=end,
            currency=currency,
            tx_type=tx_type
        )

        return PaginatedTransactionResponse(
            data=items,
            total=total,
            skip=skip,
            limit=limit
        )

    async def process_invoice_payment(self, invoice_id: int, entity_id: int, user_id: int, amount: Decimal):
        logger.info(f"💰 Invoice {invoice_id} paid: amount={amount}, user={user_id}, entity={entity_id}")
        await self.event_bus.publish("invoice.paid", {
            "invoice_id": invoice_id,
            "entity_id": entity_id,
            "user_id": user_id,
            "amount": float(amount)
        })
        return {"status": "event_published", "invoice_id": invoice_id}