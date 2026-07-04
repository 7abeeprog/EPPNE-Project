# app/domains/finance/service.py
from sqlalchemy.ext.asyncio import AsyncSession
from decimal import Decimal
import uuid
import hashlib
from datetime import datetime, timezone

from app.domains.finance.repository import WalletRepository, TransactionRepository, SystemStateRepository
from app.domains.finance.models import Wallet, AuditLog
from app.core.errors import InsufficientBalanceError, PermissionDeniedError, NotFoundError, ValidationError
from app.core.logging_conf import logger

# ===== المود الجديد: استيراد EventBus =====
from app.core.event_bus import EventBus

class FinanceService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.wallet_repo = WalletRepository(db)
        self.tx_repo = TransactionRepository(db)
        self.state_repo = SystemStateRepository(db)
        # ===== المود الجديد: تهيئة EventBus (يفترض وجود Redis client في settings) =====
        self.event_bus = EventBus()  # قد يحتاج إلى تمرير redis_client

    # ==========================================
    # دوال مساعدة
    # ==========================================
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

    async def _create_audit_log(self, user_id: int, action: str, details: dict, ip: str = None, ua: str = None):
        """✅ إنشاء سجل تدقيق"""
        log = AuditLog(
            user_id=user_id,
            action=action,
            details=details,
            ip_address=ip,
            user_agent=ua,
        )
        self.db.add(log)
        await self.db.commit()

    # ==========================================
    # 1. الرصيد
    # ==========================================
    async def get_balances(self, user_id: int, hide_crypto: bool = False) -> dict:
        wallet = await self.get_or_create_wallet(user_id)
        balances = wallet.balances or {}
        if hide_crypto:
            return {"LOYALTY_POINTS": sum(balances.values())}
        return balances

    # ==========================================
    # 2. التحويل (مع Idempotency Key)
    # ==========================================
    async def transfer(
        self,
        sender_id: int,
        receiver_email: str,
        currency: str,
        amount: Decimal,
        idempotency_key: str,
        notes: str = None,
        ip: str = None,
        ua: str = None
    ):
        """✅ تحويل الأموال مع التحقق من Idempotency Key"""
        # 1. التحقق من صحة المفتاح
        if not idempotency_key:
            raise ValidationError("Idempotency key is required")

        # 2. التحقق من تكرار العملية
        existing_tx = await self.tx_repo.get_by_idempotency_key(idempotency_key)
        if existing_tx:
            logger.warning(f"Duplicate transfer request detected: {idempotency_key}")
            return existing_tx

        # 3. التحقق من المستلم
        from app.domains.identity.repository import UserRepository
        user_repo = UserRepository(self.db)
        receiver = await user_repo.get_by_email(receiver_email)
        if not receiver:
            raise NotFoundError("المستلم غير موجود")

        # 4. التحقق من وضع النظام
        state = await self.state_repo.get_state()
        if state.crypto_mode == "POINTS_ONLY" and currency != "LOYALTY_POINTS":
            raise PermissionDeniedError("العملات المشفرة معطلة حالياً")

        # 5. 🔥 قفل المحافظ بترتيب تصاعدي (منع Deadlock)
        first_id, second_id = sorted([sender_id, receiver.id])
        first_wallet = await self.get_or_create_wallet_for_update(first_id)
        second_wallet = await self.get_or_create_wallet_for_update(second_id)

        sender_wallet = first_wallet if first_id == sender_id else second_wallet
        receiver_wallet = second_wallet if second_id == receiver.id else first_wallet

        # 6. التحقق من تجميد المحفظة
        if sender_wallet.is_frozen:
            raise PermissionDeniedError("محفظتك مجمدة. يرجى التواصل مع الدعم.")
        if receiver_wallet.is_frozen:
            raise PermissionDeniedError("محفظة المستلم مجمدة.")

        # 7. التحقق من الرصيد
        sender_balances = sender_wallet.balances.copy()
        sender_current = Decimal(str(sender_balances.get(currency, 0)))
        if sender_current < amount:
            raise InsufficientBalanceError(f"رصيد غير كافٍ من {currency}")

        # 8. تحديث الأرصدة
        sender_balances[currency] = float(sender_current - amount)
        receiver_balances = receiver_wallet.balances.copy()
        receiver_balances[currency] = receiver_balances.get(currency, 0) + float(amount)

        await self.wallet_repo.update_balances(sender_wallet.id, sender_balances)
        await self.wallet_repo.update_balances(receiver_wallet.id, receiver_balances)

        # 9. إنشاء المعاملة
        tx_hash = f"TX-{uuid.uuid4().hex[:12].upper()}"
        tx = await self.tx_repo.create(
            tx_hash=tx_hash,
            idempotency_key=idempotency_key,
            sender_id=sender_id,
            receiver_id=receiver.id,
            from_wallet_id=sender_wallet.id,
            to_wallet_id=receiver_wallet.id,
            amount=float(amount),
            currency=currency,
            tx_type="TRANSFER",
            status="COMPLETED",
            notes=notes,
        )

        # 10. ✅ تسجيل التدقيق
        await self._create_audit_log(
            user_id=sender_id,
            action="TRANSFER",
            details={
                "receiver_id": receiver.id,
                "receiver_email": receiver_email,
                "currency": currency,
                "amount": float(amount),
                "tx_hash": tx_hash,
            },
            ip=ip,
            ua=ua,
        )

        return tx

    # ==========================================
    # 3. الصرافة (مع Atomic Swap)
    # ==========================================
    async def swap(self, user_id: int, from_currency: str, to_currency: str, amount_in: Decimal):
        if from_currency == to_currency:
            raise ValidationError("لا يمكن تحويل العملة لنفسها")

        state = await self.state_repo.get_state()
        if state.crypto_mode == "POINTS_ONLY":
            raise PermissionDeniedError("خدمة الصرافة معطلة في وضع النقاط فقط")

        rates = state.exchange_rates
        if from_currency not in rates or to_currency not in rates:
            raise ValidationError("عملة غير مدعومة")

        value_in_base = float(amount_in) * rates[from_currency]
        amount_out = Decimal(value_in_base / rates[to_currency])

        # 🔥 تنفيذ العملية داخل معاملة ذرية (Atomic)
        async with self.db.begin_nested():
            wallet = await self.get_or_create_wallet_for_update(user_id)
            
            # التحقق من التجميد
            if wallet.is_frozen:
                raise PermissionDeniedError("محفظتك مجمدة")

            balances = wallet.balances.copy()
            current_from = Decimal(str(balances.get(from_currency, 0)))
            if current_from < amount_in:
                raise InsufficientBalanceError(f"رصيد غير كافٍ من {from_currency}")

            # تحديث الرصيد
            balances[from_currency] = float(current_from - amount_in)
            balances[to_currency] = balances.get(to_currency, 0) + float(amount_out)
            await self.wallet_repo.update_balances(wallet.id, balances)

            # إنشاء معاملات الصرافة
            tx_hash_out = f"SWAP-OUT-{uuid.uuid4().hex[:12].upper()}"
            tx_hash_in = f"SWAP-IN-{uuid.uuid4().hex[:12].upper()}"

            await self.tx_repo.create(
                tx_hash=tx_hash_out,
                sender_id=user_id,
                from_wallet_id=wallet.id,
                amount=float(amount_in),
                currency=from_currency,
                exchange_rate_applied=rates[from_currency] / rates[to_currency],
                tx_type="SWAP_OUT",
                status="COMPLETED",
            )
            await self.tx_repo.create(
                tx_hash=tx_hash_in,
                receiver_id=user_id,
                to_wallet_id=wallet.id,
                amount=float(amount_out),
                currency=to_currency,
                exchange_rate_applied=rates[to_currency] / rates[from_currency],
                tx_type="SWAP_IN",
                status="COMPLETED",
            )

            # ✅ تسجيل التدقيق
            await self._create_audit_log(
                user_id=user_id,
                action="SWAP",
                details={
                    "from_currency": from_currency,
                    "from_amount": float(amount_in),
                    "to_currency": to_currency,
                    "to_amount": float(amount_out),
                    "rate": rates[to_currency] / rates[from_currency],
                },
            )

        return {
            "from_amount": float(amount_in),
            "from_currency": from_currency,
            "to_amount": float(amount_out),
            "to_currency": to_currency,
            "rate_applied": rates[to_currency] / rates[from_currency]
        }

    # ==========================================
    # 4. طباعة العملات (مع التحقق من Max Supply)
    # ==========================================
    async def mint_currency(self, admin_id: int, currency: str, amount: Decimal, ip: str = None, ua: str = None):
        # 1. التحقق من الحد الأقصى
        state = await self.state_repo.get_state()
        current_supply = state.total_supply.get(currency, 0)
        max_supply = state.max_supply.get(currency, 0)

        if current_supply + float(amount) > max_supply:
            raise ValidationError(f"لا يمكن سك {currency}: سيتم تجاوز الحد الأقصى ({max_supply})")

        # 2. تحديث المحفظة
        wallet = await self.get_or_create_wallet_for_update(admin_id)
        balances = wallet.balances.copy()
        balances[currency] = balances.get(currency, 0) + float(amount)
        await self.wallet_repo.update_balances(wallet.id, balances)

        # 3. تحديث إجمالي العرض في SystemState
        new_total = current_supply + float(amount)
        state.total_supply[currency] = new_total
        state.updated_by_id = admin_id
        await self.db.commit()

        # 4. إنشاء المعاملة
        tx_hash = f"MINT-{uuid.uuid4().hex[:12].upper()}"
        tx = await self.tx_repo.create(
            tx_hash=tx_hash,
            receiver_id=admin_id,
            to_wallet_id=wallet.id,
            amount=float(amount),
            currency=currency,
            tx_type="MINT",
            status="COMPLETED",
            notes=f"سك عملات سيادية من البنك المركزي. العرض الجديد: {new_total}",
        )

        # 5. ✅ تسجيل التدقيق
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

    # ==========================================
    # 5. التاريخ المالي (مع Pagination حقيقي)
    # ==========================================
    async def get_transaction_history(self, user_id: int, skip: int = 0, limit: int = 20):
        """✅ جلب التاريخ المالي مع Pagination حقيقي"""
        return await self.tx_repo.get_by_user_paginated(user_id, skip, limit)

    # ==========================================
    # 🆕 المود الجديد: معالجة دفع الفاتورة ونشر حدث invoice.paid
    # ==========================================
    async def process_invoice_payment(self, invoice_id: int, entity_id: int, user_id: int, amount: Decimal):
        """
        دالة نموذجية لمعالجة نجاح الدفع، تقوم بتحديث حالة الفاتورة (يفترض وجود خدمة الفواتير)
        ثم تنشر حدث invoice.paid عبر EventBus.
        """
        # 1. تحديث حالة الفاتورة (هنا نفترض وجود InvoiceService)
        # from app.domains.invoice.service import InvoiceService
        # invoice_service = InvoiceService(self.db)
        # invoice = await invoice_service.mark_as_paid(invoice_id)
        # في هذا المثال نقوم فقط بتسجيل العملية
        logger.info(f"💰 Invoice {invoice_id} paid: amount={amount}, user={user_id}, entity={entity_id}")

        # 2. نشر الحدث (المود الجديد)
        await self.event_bus.publish("invoice.paid", {
            "invoice_id": invoice_id,
            "entity_id": entity_id,
            "user_id": user_id,
            "amount": float(amount)
        })
        return {"status": "event_published", "invoice_id": invoice_id}