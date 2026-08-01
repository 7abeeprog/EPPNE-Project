# app/domains/finance/service.py
from sqlalchemy.ext.asyncio import AsyncSession
from decimal import Decimal
import uuid
from datetime import datetime, timezone
from typing import Optional, cast

from app.domains.finance.repository import WalletRepository, TransactionRepository, SystemStateRepository, AuditLogRepository
from app.domains.finance.models import Wallet
from app.domains.finance.schemas import PaginatedTransactionResponse, TransactionResponse
from app.core.errors import InsufficientBalanceError, PermissionDeniedError, NotFoundError, ValidationError
from app.core.logging_conf import logger
from app.core.event_bus import EventBus
from app.domains.identity.models import User
from app.domains.identity.repository import UserRepository


class FinanceService:
    def __init__(self, db: AsyncSession, tenant_id: int):
        self.db = db
        self.tenant_id = tenant_id
        self.wallet_repo = WalletRepository(db)
        self.tx_repo = TransactionRepository(db)
        self.state_repo = SystemStateRepository(db)
        self.audit_repo = AuditLogRepository(db)
        self.event_bus = EventBus()

    async def get_or_create_wallet(self, user_id: int) -> Wallet:
        wallet = await self.wallet_repo.get_by_user_id(user_id, self.tenant_id)
        if not wallet:
            wallet = await self.wallet_repo.create(user_id, self.tenant_id)
        return wallet

    async def get_or_create_wallet_for_update(self, user_id: int) -> Wallet:
        wallet = await self.wallet_repo.get_by_user_id_for_update(user_id, self.tenant_id)
        if not wallet:
            wallet = await self.wallet_repo.create(user_id, self.tenant_id)
            wallet = await self.wallet_repo.get_by_user_id_for_update(user_id, self.tenant_id)
        return wallet

    async def _create_audit_log(self, user_id: int, action: str, details: dict, ip: Optional[str] = None, ua: Optional[str] = None):
        await self.audit_repo.create(
            user_id=user_id,
            tenant_id=self.tenant_id,
            action=action,
            details=details,
            ip_address=ip,
            user_agent=ua
        )

    async def get_balances(self, user_id: int, hide_crypto: bool = False) -> dict:
        wallet = await self.get_or_create_wallet(user_id)
        balances = getattr(wallet, "balances", {})
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

        existing_tx = await self.tx_repo.get_by_idempotency_key(idempotency_key, self.tenant_id)
        if existing_tx:
            logger.warning(f"Duplicate transfer request detected: {idempotency_key}")
            return existing_tx

        user_repo = UserRepository(self.db)
        receiver = await user_repo.get_by_email(receiver_email, self.tenant_id)
        if not receiver:
            raise NotFoundError("المستلم غير موجود")

        if receiver.tenant_id != self.tenant_id:
            raise PermissionDeniedError("المستلم لا يخص هذا المستأجر")

        state = await self.state_repo.get_state()
        crypto_mode = str(getattr(state, "crypto_mode", "FULL_CRYPTO"))
        if crypto_mode == "POINTS_ONLY" and currency != "LOYALTY_POINTS":
            raise PermissionDeniedError("العملات المشفرة معطلة حالياً")

        amount_decimal = Decimal(str(amount))

        async with self.db.begin_nested():
            first_id, second_id = sorted([sender_id, cast(int, receiver.id)])
            first_wallet = await self.get_or_create_wallet_for_update(first_id)
            second_wallet = await self.get_or_create_wallet_for_update(second_id)

            sender_wallet = first_wallet if first_id == sender_id else second_wallet
            receiver_wallet = second_wallet if second_id == receiver.id else first_wallet

            # 🛠️ تجاهل خطأ Pylance باستخدام # type: ignore
            if cast(bool, sender_wallet.is_frozen):  # type: ignore
                raise PermissionDeniedError("محفظتك مجمدة. يرجى التواصل مع الدعم.")
            if cast(bool, receiver_wallet.is_frozen):  # type: ignore
                raise PermissionDeniedError("محفظة المستلم مجمدة.")

            sender_balances = getattr(sender_wallet, "balances", {}).copy()
            sender_current = Decimal(str(sender_balances.get(currency, 0)))
            if sender_current < amount_decimal:
                raise InsufficientBalanceError(f"رصيد غير كافٍ من {currency}")

            sender_balances[currency] = float(sender_current - amount_decimal)
            receiver_balances = getattr(receiver_wallet, "balances", {}).copy()
            receiver_balances[currency] = float(Decimal(str(receiver_balances.get(currency, 0))) + amount_decimal)

            await self.wallet_repo.update_balances(cast(int, sender_wallet.id), sender_balances)
            await self.wallet_repo.update_balances(cast(int, receiver_wallet.id), receiver_balances)

            tx_hash = f"TX-{uuid.uuid4().hex[:12].upper()}"
            tx = await self.tx_repo.create(
                tx_hash=tx_hash,
                idempotency_key=idempotency_key,
                sender_id=sender_id,
                receiver_id=receiver.id,
                from_wallet_id=sender_wallet.id,
                to_wallet_id=receiver_wallet.id,
                amount=float(amount_decimal),
                currency=currency,
                tx_type="TRANSFER",
                status="COMPLETED",
                notes=notes,
            )

        await self._create_audit_log(
            user_id=sender_id,
            action="TRANSFER",
            details={
                "receiver_id": receiver.id,
                "receiver_email": receiver_email,
                "currency": currency,
                "amount": float(amount_decimal),
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

        existing_tx = await self.tx_repo.get_by_idempotency_key(idempotency_key, self.tenant_id)
        if existing_tx:
            logger.warning(f"Duplicate swap request detected: {idempotency_key}")
            return existing_tx

        state = await self.state_repo.get_state()
        crypto_mode = str(getattr(state, "crypto_mode", "FULL_CRYPTO"))
        if crypto_mode == "POINTS_ONLY":
            raise PermissionDeniedError("خدمة الصرافة معطلة في وضع النقاط فقط")

        rates = getattr(state, "exchange_rates", {}).copy()
        if from_currency not in rates or to_currency not in rates:
            raise ValidationError("عملة غير مدعومة")

        amount_in_decimal = Decimal(str(amount_in))
        value_in_base = amount_in_decimal * Decimal(str(rates[from_currency]))
        amount_out = value_in_base / Decimal(str(rates[to_currency]))

        async with self.db.begin_nested():
            wallet = await self.get_or_create_wallet_for_update(user_id)

            if cast(bool, wallet.is_frozen):  # type: ignore
                raise PermissionDeniedError("محفظتك مجمدة")

            balances = getattr(wallet, "balances", {}).copy()
            current_from = Decimal(str(balances.get(from_currency, 0)))
            if current_from < amount_in_decimal:
                raise InsufficientBalanceError(f"رصيد غير كافٍ من {from_currency}")

            balances[from_currency] = float(current_from - amount_in_decimal)
            balances[to_currency] = float(Decimal(str(balances.get(to_currency, 0))) + amount_out)
            await self.wallet_repo.update_balances(cast(int, wallet.id), balances)

            tx_hash_out = f"SWAP-OUT-{uuid.uuid4().hex[:12].upper()}"
            tx_hash_in = f"SWAP-IN-{uuid.uuid4().hex[:12].upper()}"

            await self.tx_repo.create(
                tx_hash=tx_hash_out,
                idempotency_key=f"{idempotency_key}-out",
                sender_id=user_id,
                from_wallet_id=wallet.id,
                amount=float(amount_in_decimal),
                currency=from_currency,
                exchange_rate_applied=float(Decimal(str(rates[from_currency])) / Decimal(str(rates[to_currency]))),
                tx_type="SWAP_OUT",
                status="COMPLETED",
            )
            await self.tx_repo.create(
                tx_hash=tx_hash_in,
                idempotency_key=f"{idempotency_key}-in",
                receiver_id=user_id,
                to_wallet_id=wallet.id,
                amount=float(amount_out),
                currency=to_currency,
                exchange_rate_applied=float(Decimal(str(rates[to_currency])) / Decimal(str(rates[from_currency]))),
                tx_type="SWAP_IN",
                status="COMPLETED",
            )

        await self._create_audit_log(
            user_id=user_id,
            action="SWAP",
            details={
                "from_currency": from_currency,
                "from_amount": float(amount_in_decimal),
                "to_currency": to_currency,
                "to_amount": float(amount_out),
                "rate": float(Decimal(str(rates[to_currency])) / Decimal(str(rates[from_currency]))),
            },
            ip=ip,
            ua=ua,
        )

        return {
            "from_amount": float(amount_in_decimal),
            "from_currency": from_currency,
            "to_amount": float(amount_out),
            "to_currency": to_currency,
            "rate_applied": float(Decimal(str(rates[to_currency])) / Decimal(str(rates[from_currency]))),
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

        existing_tx = await self.tx_repo.get_by_idempotency_key(idempotency_key, self.tenant_id)
        if existing_tx:
            logger.warning(f"Duplicate mint request detected: {idempotency_key}")
            return existing_tx

        state = await self.state_repo.get_state()
        current_supply = getattr(state, "total_supply", {}).get(currency, 0)
        max_supply = getattr(state, "max_supply", {}).get(currency, 0)

        amount_decimal = Decimal(str(amount))
        if Decimal(str(current_supply)) + amount_decimal > Decimal(str(max_supply)):
            raise ValidationError(f"لا يمكن سك {currency}: سيتم تجاوز الحد الأقصى ({max_supply})")

        async with self.db.begin_nested():
            wallet = await self.get_or_create_wallet_for_update(admin_id)
            balances = getattr(wallet, "balances", {}).copy()
            balances[currency] = float(Decimal(str(balances.get(currency, 0))) + amount_decimal)
            await self.wallet_repo.update_balances(cast(int, wallet.id), balances)

            new_total = float(Decimal(str(current_supply)) + amount_decimal)
            setattr(state, "total_supply", {**getattr(state, "total_supply", {}), currency: new_total})
            setattr(state, "updated_by_id", admin_id)
            await self.db.commit()

            tx_hash = f"MINT-{uuid.uuid4().hex[:12].upper()}"
            tx = await self.tx_repo.create(
                tx_hash=tx_hash,
                idempotency_key=idempotency_key,
                receiver_id=admin_id,
                to_wallet_id=wallet.id,
                amount=float(amount_decimal),
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
                "amount": float(amount_decimal),
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

        result = await self.tx_repo.get_by_user_paginated(
            user_id=user_id,
            tenant_id=self.tenant_id,
            skip=skip,
            limit=limit,
            start_date=start,
            end_date=end,
            currency=currency,
            tx_type=tx_type
        )

        total = await self.tx_repo.count_by_user(
            user_id=user_id,
            tenant_id=self.tenant_id,
            start_date=start,
            end_date=end,
            currency=currency,
            tx_type=tx_type
        )

        return PaginatedTransactionResponse(
            data=result["items"],
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