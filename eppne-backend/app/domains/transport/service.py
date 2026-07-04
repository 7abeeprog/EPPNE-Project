# app/domains/transport/service.py (الإصدار النهائي المتكامل)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import update
from datetime import datetime, timedelta
from decimal import Decimal
import uuid
import bleach

from app.domains.transport.repository import TransportRepository
# التعديل الصحيح
from app.domains.finance.service import FinanceService as InvoicingService
from app.domains.finance.service import FinanceService as InvoicingService
from app.domains.affiliate.service import AffiliateService
from app.domains.saas.service import SaaSControlService as SaaSSubscriptionService
from app.domains.ai_agents.service import AIAgentsService
from app.domains.ai_governance.service import AIGovernanceService
from app.domains.communications.service import CommunicationsService
from app.core.errors import NotFoundError, InsufficientBalanceError, PermissionDeniedError
from app.core.idempotency import check_idempotency, store_idempotency_result
from app.core.audit import audit_log
from app.core.event_bus import EventBus
from app.core.redis_client import redis_client
from app.core.logging_conf import logger
from app.domains.transport.models import (
    Vehicle, Trip, TripStatus, TripBooking, DeliveryTask, VehicleStatus,
    Route
)
from app.domains.identity.repository import UserRepository
from app.domains.identity.models import User


class TransportService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = TransportRepository(db)
        self.finance = FinanceService(db)
        self.invoicing = InvoicingService(db)
        self.affiliate = AffiliateService(db)
        self.saas = SaaSSubscriptionService(db)
        self.ai = AIAgentsService(db)
        self.governance = AIGovernanceService(db)
        self.communications = CommunicationsService(db)
        self.event_bus = EventBus(redis_client)
        self.redis = redis_client
        self.user_repo = UserRepository(db)

    # ========== التحقق من صلاحيات SaaS ==========
    async def _check_saas_limits(self, tenant_id: int, feature: str = "transport"):
        subscription = await self.saas.get_active_subscription(tenant_id)
        if not subscription:
            raise PermissionDeniedError("No active subscription found.")
        features = subscription.features or {}
        if not features.get(feature, False):
            raise PermissionDeniedError("Transport feature is not included in your current plan.")
        return subscription, features

    # ========== التحقق من حوكمة الذكاء الاصطناعي ==========
    async def _check_ai_governance(self, tenant_id: int, user_id: int, action: str, cost: Decimal):
        try:
            return await self.governance.check_and_consume(
                tenant_id=tenant_id,
                agent_id=3,  # وكيل TRANSPORT_OPTIMIZER
                user_id=user_id,
                tokens=50,
                cost=cost
            )
        except Exception as e:
            logger.warning(f"AI Governance check failed: {e}")
            return None

    # ========== إنشاء مسار (مع تحسين الذكاء الاصطناعي) ==========
    async def create_route(self, tenant_id: int, data: dict) -> Route:
        await self._check_saas_limits(tenant_id, "transport")

        # استدعاء وكيل TRANSPORT_OPTIMIZER لتحسين المسار
        try:
            ai_result = await self.ai.execute_agent_action(
                agent_id=3,  # وكيل TRANSPORT_OPTIMIZER
                tenant_id=tenant_id,
                action_type="ANALYZE_SENSOR",
                payload={
                    "start_hub": data["start_hub_id"],
                    "end_hub": data["end_hub_id"],
                    "waypoints": data.get("waypoints", []),
                    "distance_km": float(data["distance_km"])
                },
                executor_user_id=0
            )
            if ai_result and "optimized_path" in ai_result.get("result", {}):
                optimized = ai_result["result"]["optimized_path"]
                data["distance_km"] = Decimal(str(optimized.get("distance", data["distance_km"])))
                data["estimated_duration_minutes"] = optimized.get("duration", data["estimated_duration_minutes"])
                data["waypoints"] = optimized.get("waypoints", data.get("waypoints", []))
                logger.info(f"AI optimized route: {optimized}")
        except Exception as e:
            logger.warning(f"AI optimization failed, using original route: {e}")

        return await self.repo.create_route(tenant_id=tenant_id, **data)

    # ========== حجز رحلة (مع Idempotency, SaaS, Affiliate, Invoicing, AI Governance) ==========
    async def book_trip(
        self,
        tenant_id: int,
        passenger_id: int,
        data: dict,
        idempotency_key: str = None
    ) -> TripBooking:
        # 1. التحقق من SaaS
        await self._check_saas_limits(tenant_id, "transport")

        # 2. التحقق من Idempotency
        if idempotency_key:
            cached = await check_idempotency(idempotency_key)
            if cached:
                return cached

        # 3. جلب الرحلة والتحقق من صلاحيتها
        trip = await self.repo.get_trip(data["trip_id"], tenant_id)
        if not trip or trip.status != TripStatus.SCHEDULED:
            raise NotFoundError("Trip not available")

        # 4. التحقق من حوكمة الذكاء الاصطناعي
        fare = trip.base_fare_mrusdt * Decimal(data.get("seats_count", 1))
        await self._check_ai_governance(tenant_id, passenger_id, "BOOK_TRIP", fare)

        # 5. تنفيذ التحويل المالي
        driver = await self._get_user_by_id(trip.driver_id)
        try:
            tx_hash = await self.finance.transfer(
                sender_id=passenger_id,
                receiver_email=driver.email,
                currency="MR_USDT",
                amount=fare,
                notes=f"Trip booking {trip.id}",
                idempotency_key=idempotency_key
            )
        except InsufficientBalanceError:
            raise PermissionDeniedError("Insufficient balance")

        # 6. إنشاء الحجز
        booking = await self.repo.create_booking(
            tenant_id=tenant_id,
            trip_id=trip.id,
            passenger_id=passenger_id,
            booking_type="PASSENGER",
            seats_count=data.get("seats_count", 1),
            fare_paid_mrusdt=fare,
            status="CONFIRMED",
            idempotency_key=idempotency_key
        )

        # 7. إنشاء فاتورة
        await self.invoicing.create_invoice(
            entity_id=tenant_id,
            user_id=passenger_id,
            amount=fare,
            description=f"Trip booking #{trip.id} - {trip.route_id}",
            due_date=datetime.utcnow() + timedelta(days=3)
        )

        # 8. تسجيل الإحالة
        await self._register_affiliate_commission(passenger_id, tenant_id, fare)

        # 9. تسجيل التدقيق
        await audit_log(
            user_id=passenger_id,
            tenant_id=tenant_id,
            action="TRIP_BOOKED",
            resource_id=booking.id,
            details={"trip_id": trip.id, "amount": float(fare)}
        )

        # 10. نشر حدث للأتمتة والإشعارات
        await self.event_bus.publish("transport.booking.confirmed", {
            "booking_id": booking.id,
            "trip_id": trip.id,
            "passenger_id": passenger_id,
            "tenant_id": tenant_id
        })

        # 11. إرسال إشعار للمستخدم
        await self._send_notification(
            user_id=passenger_id,
            title="تم تأكيد حجز الرحلة",
            body=f"تم حجز رحلتك #{trip.id} بنجاح. السعر: {fare} MR_USDT"
        )

        # 12. تخزين نتيجة Idempotency
        if idempotency_key:
            await store_idempotency_result(idempotency_key, booking)

        return booking

    # ========== بدء الرحلة (مع Audit و EventBus) ==========
    async def start_trip(self, tenant_id: int, trip_id: int, driver_id: int, actual_start: datetime) -> Trip:
        trip = await self.repo.get_trip(trip_id, tenant_id)
        if not trip or trip.driver_id != driver_id:
            raise PermissionDeniedError("Not authorized to start this trip")
        if trip.status != TripStatus.SCHEDULED:
            raise ValueError("Trip cannot be started")

        # التحقق من صلاحية المركبة
        vehicle = await self.repo.get_vehicle(trip.vehicle_id, tenant_id)
        if not vehicle or vehicle.status != VehicleStatus.AVAILABLE:
            raise ValueError("Vehicle not available")

        result = await self.repo.start_trip(trip_id, tenant_id, actual_start)

        # تسجيل التدقيق
        await audit_log(
            user_id=driver_id,
            tenant_id=tenant_id,
            action="TRIP_STARTED",
            resource_id=trip_id,
            details={"vehicle_id": trip.vehicle_id}
        )

        # نشر حدث للأتمتة
        await self.event_bus.publish("transport.trip.started", {
            "trip_id": trip_id,
            "driver_id": driver_id,
            "tenant_id": tenant_id
        })

        return result

    # ========== إنهاء الرحلة (مع حسابات الكربون والفوترة) ==========
    async def complete_trip(
        self,
        tenant_id: int,
        trip_id: int,
        driver_id: int,
        actual_end: datetime,
        total_distance_km: float
    ) -> Trip:
        trip = await self.repo.get_trip(trip_id, tenant_id)
        if not trip or trip.driver_id != driver_id:
            raise PermissionDeniedError("Not authorized")
        if trip.status != TripStatus.ONGOING:
            raise ValueError("Trip is not ongoing")

        vehicle = await self.repo.get_vehicle(trip.vehicle_id, tenant_id)
        if not vehicle:
            raise NotFoundError("Vehicle not found")

        carbon = self.calculate_carbon(vehicle, total_distance_km)
        result = await self.repo.complete_trip(trip_id, tenant_id, actual_end, total_distance_km, carbon)

        # تسجيل التدقيق
        await audit_log(
            user_id=driver_id,
            tenant_id=tenant_id,
            action="TRIP_COMPLETED",
            resource_id=trip_id,
            details={"distance": total_distance_km, "carbon": carbon}
        )

        # نشر حدث للأتمتة
        await self.event_bus.publish("transport.trip.completed", {
            "trip_id": trip_id,
            "driver_id": driver_id,
            "tenant_id": tenant_id,
            "distance": total_distance_km,
            "carbon": carbon
        })

        return result

    # ========== دفع التوصيل (مع Idempotency, Affiliate, Invoicing) ==========
    async def pay_delivery(
        self,
        tenant_id: int,
        task_id: int,
        payer_id: int,
        idempotency_key: str = None
    ) -> DeliveryTask:
        # 1. التحقق من SaaS
        await self._check_saas_limits(tenant_id, "transport")

        # 2. التحقق من Idempotency
        if idempotency_key:
            cached = await check_idempotency(idempotency_key)
            if cached:
                return cached

        task = await self.repo.get_delivery_task(task_id, tenant_id)
        if not task or task.sender_id != payer_id:
            raise NotFoundError("Delivery task not found")
        if task.payment_tx_hash:
            raise ValueError("Already paid")
        if not task.trip_id:
            raise ValueError("Delivery not assigned to a trip")

        # 3. جلب السائق
        trip = await self.repo.get_trip(task.trip_id, tenant_id)
        if not trip:
            raise NotFoundError("Trip not found")
        driver = await self._get_user_by_id(trip.driver_id)

        # 4. تنفيذ التحويل المالي
        try:
            tx_hash = await self.finance.transfer(
                sender_id=payer_id,
                receiver_email=driver.email,
                currency="MR_USDT",
                amount=task.delivery_fee_mrusdt,
                notes=f"Delivery fee for task {task.id}",
                idempotency_key=idempotency_key
            )
        except InsufficientBalanceError:
            raise PermissionDeniedError("Insufficient balance")

        # 5. تحديث حالة الدفع
        await self.db.execute(
            update(DeliveryTask).where(DeliveryTask.id == task_id).values(
                payment_tx_hash=tx_hash
            )
        )
        await self.db.commit()

        # 6. إنشاء فاتورة
        await self.invoicing.create_invoice(
            entity_id=tenant_id,
            user_id=payer_id,
            amount=task.delivery_fee_mrusdt,
            description=f"Delivery task #{task.id}",
            due_date=datetime.utcnow() + timedelta(days=3)
        )

        # 7. تسجيل الإحالة
        await self._register_affiliate_commission(payer_id, tenant_id, task.delivery_fee_mrusdt)

        # 8. تسجيل التدقيق
        await audit_log(
            user_id=payer_id,
            tenant_id=tenant_id,
            action="DELIVERY_PAID",
            resource_id=task.id,
            details={"amount": float(task.delivery_fee_mrusdt)}
        )

        # 9. نشر حدث للأتمتة
        await self.event_bus.publish("transport.delivery.paid", {
            "task_id": task.id,
            "payer_id": payer_id,
            "tenant_id": tenant_id
        })

        if idempotency_key:
            await store_idempotency_result(idempotency_key, task)

        return await self.repo.get_delivery_task(task_id, tenant_id)

    # ========== دوال مساعدة ==========
    @staticmethod
    def calculate_carbon(vehicle: Vehicle, distance_km: float) -> float:
        return float(vehicle.carbon_per_km) * distance_km

    async def _get_user_by_id(self, user_id: int) -> User:
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise NotFoundError("User not found")
        return user

    async def _register_affiliate_commission(self, user_id: int, tenant_id: int, amount: Decimal):
        try:
            user = await self.user_repo.get_by_id(user_id)
            if user and user.referred_by:
                commission = amount * Decimal("0.02")  # 2%
                await self.affiliate.register_commission(
                    affiliate_id=user.referred_by,
                    user_id=user_id,
                    amount=commission,
                    description="Transport transaction commission",
                    status="PENDING"
                )
        except Exception as e:
            logger.error(f"Affiliate registration failed: {e}")

    async def _send_notification(self, user_id: int, title: str, body: str):
        try:
            await self.communications.send_notification(
                user_id=user_id,
                title=title,
                body=body,
                channel="IN_APP"
            )
        except Exception as e:
            logger.error(f"Notification failed: {e}")