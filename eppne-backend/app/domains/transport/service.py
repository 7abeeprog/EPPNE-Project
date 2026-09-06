# pyright: reportGeneralTypeIssues=false
# pyright: reportCallIssue=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportArgumentType=false

# app/domains/transport/service.py (الإصدار النهائي المتكامل المصحح)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import update
from sqlalchemy.exc import IntegrityError
from datetime import datetime, timedelta
from decimal import Decimal
import uuid
import bleach
from typing import Optional, Dict, Any, List, cast

from app.domains.transport.repository import TransportRepository
from app.domains.finance.service import FinanceService
from app.domains.invoicing.service import InvoicingService
from app.domains.affiliate.service import AffiliateService
from app.domains.saas.service import SaaSControlService as SaaSSubscriptionService
from app.domains.ai_agents.service import AIAgentsService
from app.domains.ai_governance.service import AIGovernanceService
from app.domains.communications.service import CommunicationsService
from app.core.errors import NotFoundError, InsufficientBalanceError, PermissionDeniedError, ValidationError
from app.core.idempotency import get_idempotency_result, store_idempotency_result
from app.core.audit import audit_log
from app.core.event_bus import EventBus
from app.core.redis_client import redis_client
from app.core.logging_conf import logger
from app.domains.transport.models import (
    Vehicle, Trip, TripStatus, TripBooking, DeliveryTask, VehicleStatus,
    Route, TransportHub, Fleet
)
from app.domains.identity.repository import UserRepository
from app.domains.identity.models import User


class TransportService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = TransportRepository(db)
        self.communications = CommunicationsService(db)
        self.event_bus = EventBus(cast(Any, redis_client))
        self.redis = redis_client
        self.user_repo = UserRepository(db)

    # ============================================================
    # 0. دوال Idempotency الموحّدة
    # ============================================================

    async def _validate_idempotency(self, idempotency_key: str) -> Optional[Dict[str, Any]]:
        """التحقق من وجود نتيجة مخزنة مسبقاً لمفتاح Idempotency."""
        if idempotency_key:
            cached = await get_idempotency_result(idempotency_key)
            if cached is not None:
                return cached
        return None

    async def _store_idempotency(self, idempotency_key: str, result: Dict[str, Any]):
        """تخزين نتيجة العملية بعد النجاح."""
        if idempotency_key:
            await store_idempotency_result(idempotency_key, result)

    # ========== التحقق من صلاحيات SaaS ==========
    async def _check_saas_limits(self, tenant_id: int, feature: str = "transport"):
        saas_service = SaaSSubscriptionService(self.db, tenant_id)
        has_access = await saas_service.can_access_service(feature)
        if not has_access:
            raise PermissionDeniedError("Transport feature is not included in your current plan.")
        return None, {}

    # ========== التحقق من حوكمة الذكاء الاصطناعي ==========
    async def _check_ai_governance(self, tenant_id: int, user_id: int, action: str, cost: Decimal):
        try:
            governance = AIGovernanceService(self.db, tenant_id)
            return await governance.check_and_consume(
                agent_id=3,
                user_id=user_id,
                action_type=action,
                tokens=50,
                cost=cost
            )
        except Exception as e:
            logger.warning(f"AI Governance check failed: {e}")
            return None

    # ============================================================
    # 1. المحطات (Hubs)
    # ============================================================
    async def create_hub(self, tenant_id: int, data: Dict[str, Any]) -> TransportHub:
        await self._check_saas_limits(tenant_id, "transport")
        sanitized_name = bleach.clean(data.get("name", ""), tags=[], strip=True)
        return await self.repo.create_hub(
            tenant_id=tenant_id,
            name=sanitized_name,
            hub_type=data["hub_type"],
            region=data.get("region"),
            gps_location=data["gps_location"],
            entity_id=data.get("entity_id")
        )

    async def list_hubs(
        self,
        tenant_id: int,
        hub_type: Optional[str] = None,
        skip: int = 0,
        limit: int = 50
    ) -> List[TransportHub]:
        await self._check_saas_limits(tenant_id, "transport")
        result = await self.repo.list_hubs(tenant_id, hub_type, skip, limit)
        return list(result)

    # ============================================================
    # 2. الأساطيل والمركبات (Fleets & Vehicles)
    # ============================================================
    async def create_fleet(self, tenant_id: int, data: Dict[str, Any]) -> Fleet:
        await self._check_saas_limits(tenant_id, "transport")
        sanitized_name = bleach.clean(data.get("name", ""), tags=[], strip=True)
        entity_id = data.get("entity_id", 1)
        return await self.repo.create_fleet(
            tenant_id=tenant_id,
            entity_id=entity_id,
            name=sanitized_name
        )

    async def create_vehicle(self, tenant_id: int, data: Dict[str, Any]) -> Vehicle:
        await self._check_saas_limits(tenant_id, "transport")
        sanitized_plate = bleach.clean(data.get("license_plate", ""), tags=[], strip=True)
        return await self.repo.create_vehicle(
            tenant_id=tenant_id,
            fleet_id=data["fleet_id"],
            license_plate=sanitized_plate,
            vehicle_type=data["vehicle_type"],
            capacity_kg=data.get("capacity_kg"),
            capacity_passengers=data.get("capacity_passengers"),
            fuel_type=data.get("fuel_type", "ELECTRIC"),
            carbon_per_km=data.get("carbon_per_km", Decimal(0)),
            smart_asset_id=data.get("smart_asset_id")
        )

    async def update_vehicle_location(
        self,
        tenant_id: int,
        vehicle_id: int,
        location: Dict[str, float]
    ) -> Vehicle:
        await self._check_saas_limits(tenant_id, "transport")
        return await self.repo.update_vehicle_location(vehicle_id, tenant_id, location)

    async def get_available_vehicles(
        self,
        tenant_id: int,
        fleet_id: Optional[int] = None
    ) -> List[Vehicle]:
        await self._check_saas_limits(tenant_id, "transport")
        result = await self.repo.list_available_vehicles(tenant_id, fleet_id)
        return list(result)

    async def get_vehicle(self, vehicle_id: int, tenant_id: int) -> Vehicle:
        vehicle = await self.repo.get_vehicle(vehicle_id, tenant_id)
        if not vehicle:
            raise NotFoundError("Vehicle not found")
        return vehicle

    async def list_vehicles(
        self,
        tenant_id: int,
        fleet_id: Optional[int] = None,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> List[Vehicle]:
        await self._check_saas_limits(tenant_id, "transport")
        result = await self.repo.list_vehicles(tenant_id, fleet_id, status, skip, limit)
        return list(result)

    async def update_vehicle(self, tenant_id: int, vehicle_id: int, data: Dict[str, Any]) -> Vehicle:
        await self._check_saas_limits(tenant_id, "transport")
        existing = await self.repo.get_vehicle(vehicle_id, tenant_id)
        if not existing:
            raise NotFoundError("Vehicle not found")
        update_data = {k: v for k, v in data.items() if v is not None}
        if "license_plate" in update_data:
            update_data["license_plate"] = bleach.clean(update_data["license_plate"], tags=[], strip=True)
        result = await self.repo.update_vehicle(vehicle_id, tenant_id, **update_data)
        return cast(Vehicle, result)

    async def delete_vehicle(self, tenant_id: int, vehicle_id: int) -> None:
        existing = await self.repo.get_vehicle(vehicle_id, tenant_id)
        if not existing:
            raise NotFoundError("Vehicle not found")
        try:
            await self.repo.delete_vehicle(vehicle_id, tenant_id)
        except IntegrityError:
            await self.db.rollback()
            raise ValidationError("Cannot delete a vehicle with existing trip history")

    # ============================================================
    # 2.1 الأساطيل (Fleets) — قراءة/تعديل/حذف
    # ============================================================
    async def list_fleets(self, tenant_id: int, skip: int = 0, limit: int = 50) -> List[Fleet]:
        await self._check_saas_limits(tenant_id, "transport")
        result = await self.repo.list_fleets(tenant_id, skip, limit)
        return list(result)

    async def update_fleet(self, tenant_id: int, fleet_id: int, name: str) -> Fleet:
        await self._check_saas_limits(tenant_id, "transport")
        existing = await self.repo.get_fleet(fleet_id, tenant_id)
        if not existing:
            raise NotFoundError("Fleet not found")
        sanitized_name = bleach.clean(name, tags=[], strip=True)
        result = await self.repo.update_fleet(fleet_id, tenant_id, name=sanitized_name)
        return cast(Fleet, result)

    async def delete_fleet(self, tenant_id: int, fleet_id: int) -> None:
        existing = await self.repo.get_fleet(fleet_id, tenant_id)
        if not existing:
            raise NotFoundError("Fleet not found")
        await self.repo.delete_fleet(fleet_id, tenant_id)

    # ============================================================
    # 2.2 السائقون (Drivers) — بدون كيان/دور منفصل [قرار مستخدم، جلسة
    # transport-vehicles-drivers-feature-build، 2026-09-04]: create_trip
    # أصلًا بتقبل أي user_id كـdriver_id بلا أي فحص دور، فده مجرد سرد
    # للمستخدمين النشطين بنفس التينانت — صفر migration، صفر تعديل على
    # identity/models.py أو SystemRole.
    # ============================================================
    async def list_drivers(self, tenant_id: int, skip: int = 0, limit: int = 50) -> List[User]:
        await self._check_saas_limits(tenant_id, "transport")
        return await self.user_repo.list_active_by_tenant(tenant_id, skip, limit)

    # ============================================================
    # 3. المسارات (Routes)
    # ============================================================
    async def create_route(self, tenant_id: int, data: Dict[str, Any]) -> Route:
        await self._check_saas_limits(tenant_id, "transport")

        try:
            ai_service = AIAgentsService(self.db, tenant_id)
            ai_result = await ai_service.execute_agent_action(
                agent_id=3,
                action_type="ANALYZE_SENSOR",
                payload={
                    "start_hub": data["start_hub_id"],
                    "end_hub": data["end_hub_id"],
                    "waypoints": data.get("waypoints", []),
                    "distance_km": float(data["distance_km"])
                },
                executor_user_id=0,
                idempotency_key=f"AI-ROUTE-T{tenant_id}-{uuid.uuid4().hex[:12]}"
            )
            if ai_result and "optimized_path" in ai_result.get("result", {}):
                optimized = ai_result["result"]["optimized_path"]
                data["distance_km"] = Decimal(str(optimized.get("distance", data["distance_km"])))
                data["estimated_duration_minutes"] = optimized.get("duration", data["estimated_duration_minutes"])
                data["waypoints"] = optimized.get("waypoints", data.get("waypoints", []))
                logger.info(f"AI optimized route: {optimized}")
        except Exception as e:
            logger.warning(f"AI optimization failed, using original route: {e}")

        sanitized_name = bleach.clean(data.get("name", ""), tags=[], strip=True)
        return await self.repo.create_route(
            tenant_id=tenant_id,
            name=sanitized_name,
            start_hub_id=data["start_hub_id"],
            end_hub_id=data["end_hub_id"],
            waypoints=data.get("waypoints", []),
            distance_km=data["distance_km"],
            estimated_duration_minutes=data["estimated_duration_minutes"]
        )

    async def get_route(self, route_id: int, tenant_id: int) -> Route:
        route = await self.repo.get_route(route_id, tenant_id)
        if not route:
            raise NotFoundError("Route not found")
        return route

    # ============================================================
    # 4. الرحلات (Trips)
    # ============================================================
    async def create_trip(self, tenant_id: int, data: Dict[str, Any]) -> Trip:
        await self._check_saas_limits(tenant_id, "transport")
        return await self.repo.create_trip(tenant_id=tenant_id, **data)

    async def get_trip(self, trip_id: int, tenant_id: int) -> Trip:
        trip = await self.repo.get_trip(trip_id, tenant_id)
        if not trip:
            raise NotFoundError("Trip not found")
        return trip

    async def start_trip(
        self,
        tenant_id: int,
        trip_id: int,
        driver_id: int,
        actual_start: datetime
    ) -> Trip:
        trip = await self.repo.get_trip(trip_id, tenant_id)
        if not trip or trip.driver_id != driver_id:  # type: ignore
            raise PermissionDeniedError("Not authorized to start this trip")
        if trip.status != TripStatus.SCHEDULED:  # type: ignore
            raise ValueError("Trip cannot be started")

        vehicle = await self.repo.get_vehicle(trip.vehicle_id, tenant_id)  # type: ignore
        if not vehicle or vehicle.status != VehicleStatus.AVAILABLE:  # type: ignore
            raise ValueError("Vehicle not available")

        result = await self.repo.start_trip(trip_id, tenant_id, actual_start)

        await audit_log(  # type: ignore[call-arg]
            user_id=driver_id,
            tenant_id=tenant_id,
            action="TRIP_STARTED",
            resource_id=trip_id,
            details={"vehicle_id": trip.vehicle_id}
        )

        await self.event_bus.publish("transport.trip.started", {
            "trip_id": trip_id,
            "driver_id": driver_id,
            "tenant_id": tenant_id
        })

        return result

    async def complete_trip(
        self,
        tenant_id: int,
        trip_id: int,
        driver_id: int,
        actual_end: datetime,
        total_distance_km: float
    ) -> Trip:
        trip = await self.repo.get_trip(trip_id, tenant_id)
        if not trip or trip.driver_id != driver_id:  # type: ignore
            raise PermissionDeniedError("Not authorized")
        if trip.status != TripStatus.ONGOING:  # type: ignore
            raise ValueError("Trip is not ongoing")

        vehicle = await self.repo.get_vehicle(trip.vehicle_id, tenant_id)  # type: ignore
        if not vehicle:
            raise NotFoundError("Vehicle not found")

        carbon = self.calculate_carbon(vehicle, total_distance_km)
        result = await self.repo.complete_trip(trip_id, tenant_id, actual_end, total_distance_km, carbon)

        # تسوية (settle) كل الحجوزات المؤكَّدة على الرحلة دي — الأجرة كانت
        # محجوزة (hold) وقت book_trip، وبتتحرر للسائق فعليًا دلوقتي بعد
        # اكتمال الرحلة فعلًا [قرار مستخدم، جلسة
        # transport-domain-full-build، 2026-09-01]. حجوزات company_id
        # (مش مُستخدَمة فعليًا من أي فرونت إند حاليًا) بتتخطى — تحتاج تصميم
        # فوترة شركات منفصل خارج نطاق هذه الجلسة.
        driver = await self._get_user_by_id(driver_id, tenant_id)
        finance = FinanceService(self.db, tenant_id)
        confirmed_bookings = await self.repo.list_bookings(tenant_id, trip_id=trip_id)
        for booking in confirmed_bookings:
            if booking.status != "CONFIRMED" or booking.passenger_id is None:  # type: ignore
                continue
            try:
                await finance.settle_held_funds(
                    sender_id=cast(int, booking.passenger_id),  # type: ignore
                    receiver_email=cast(str, driver.email),
                    currency="MR_USDT",
                    amount=cast(Decimal, booking.fare_paid_mrusdt),  # type: ignore
                    notes=f"Trip {trip_id} completed",
                    idempotency_key=f"SETTLE-TRIP{trip_id}-BOOKING{booking.id}",
                )
            except Exception as e:
                logger.error(f"Settlement failed for booking {booking.id} on trip {trip_id}: {e}")

        # settle_held_funds() بتعمل begin_nested() (savepoint) بس من
        # جوّه — بلا commit() صريح هنا، أي تسوية ناجحة كانت بتترجع
        # (rollback) صامتة لما الجلسة تتقفل، بلا أي استثناء يُظهر المشكلة
        # (مكتشف حيًا: held_balances فضلت زي ما هي بعد complete_trip رغم
        # نجاح settle_held_funds منطقيًا) [جلسة
        # transport-domain-full-build، 2026-09-01].
        await self.db.commit()

        await audit_log(  # type: ignore[call-arg]
            user_id=driver_id,
            tenant_id=tenant_id,
            action="TRIP_COMPLETED",
            resource_id=trip_id,
            details={"distance": total_distance_km, "carbon": carbon}
        )

        await self.event_bus.publish("transport.trip.completed", {
            "trip_id": trip_id,
            "driver_id": driver_id,
            "tenant_id": tenant_id,
            "distance": total_distance_km,
            "carbon": carbon
        })

        return result

    async def get_my_trips(
        self,
        tenant_id: int,
        driver_id: int,
        status_filter: Optional[str] = None,
        skip: int = 0,
        limit: int = 50
    ) -> List[Trip]:
        await self._check_saas_limits(tenant_id, "transport")
        result = await self.repo.list_trips(tenant_id, driver_id, status_filter, skip, limit)
        return list(result)

    # ============================================================
    # 5. الحجوزات (Bookings) – مع Idempotency محسّن
    # ============================================================
    async def book_trip(
        self,
        tenant_id: int,
        passenger_id: int,
        data: Dict[str, Any],
        idempotency_key: Optional[str] = None
    ) -> TripBooking:
        await self._check_saas_limits(tenant_id, "transport")

        # 1. التحقق من Idempotency
        if idempotency_key:
            cached = await self._validate_idempotency(idempotency_key)
            if cached is not None:
                booking_id = cached.get("booking_id")
                if booking_id:
                    booking = await self.repo.get_booking(booking_id, tenant_id)
                    if booking:
                        return booking
                raise ValidationError("Idempotency record exists but booking not found.")

        trip = await self.repo.get_trip(data["trip_id"], tenant_id)
        if not trip or trip.status != TripStatus.SCHEDULED:  # type: ignore
            raise NotFoundError("Trip not available")

        fare = trip.base_fare_mrusdt * Decimal(data.get("seats_count", 1))  # type: ignore
        await self._check_ai_governance(tenant_id, passenger_id, "BOOK_TRIP", cast(Decimal, fare))

        driver = await self._get_user_by_id(cast(int, trip.driver_id), tenant_id)  # type: ignore

        finance = FinanceService(self.db, tenant_id)
        invoicing = InvoicingService(self.db, tenant_id)
        async with self.db.begin_nested():
            try:
                # حجز (hold) بدل تحويل مباشر — الأجرة بتتحرر (settle) للسائق
                # فقط لما الرحلة تكتمل فعليًا (complete_trip)، أو تترجع
                # (release) لو الحجز اتلغى قبل الرحلة (cancel_booking).
                # نفس نمط tenders_auctions.place_live_bid [قرار مستخدم،
                # جلسة transport-domain-full-build، 2026-09-01].
                await finance.hold_funds(
                    user_id=passenger_id,
                    amount=cast(Decimal, fare),
                    currency="MR_USDT",
                    description=f"Trip booking hold - trip {trip.id}",
                    idempotency_key=idempotency_key or ""
                )
            except InsufficientBalanceError:
                raise PermissionDeniedError("Insufficient balance")

            booking = await self.repo.create_booking(
                tenant_id=tenant_id,
                trip_id=trip.id,
                passenger_id=passenger_id,
                booking_type=data.get("booking_type", "PASSENGER"),
                seats_count=data.get("seats_count", 1),
                weight_kg=data.get("weight_kg"),
                fare_paid_mrusdt=cast(Decimal, fare),
                status="CONFIRMED",
                idempotency_key=idempotency_key
            )

            await self._register_affiliate_commission(passenger_id, tenant_id, cast(Decimal, fare))

            await audit_log(  # type: ignore[call-arg]
                user_id=passenger_id,
                tenant_id=tenant_id,
                action="TRIP_BOOKED",
                resource_id=booking.id,
                details={"trip_id": trip.id, "amount": float(cast(Decimal, fare))}
            )

            await self.event_bus.publish("transport.booking.confirmed", {
                "booking_id": booking.id,
                "trip_id": trip.id,
                "passenger_id": passenger_id,
                "tenant_id": tenant_id
            })

            await self._send_notification(
                user_id=passenger_id,
                title="تم تأكيد حجز الرحلة",
                body=f"تم حجز رحلتك #{trip.id} بنجاح. السعر: {fare} MR_USDT"
            )

        await self.db.commit()

        try:
            await invoicing.create_invoice(
                entity_id=tenant_id,
                user_id=passenger_id,
                amount=cast(Decimal, fare),
                description=f"Trip booking #{trip.id} - {trip.route_id}",
                due_date=datetime.utcnow() + timedelta(days=3)
            )
        except Exception as e:
            # rollback + refresh إجباريان قبل أي وصول لاحق لـbooking.id —
            # فشل create_invoice (IntegrityError شائع، راجع backlog
            # invoicing-generate-invoice-number-count-based-collision)
            # يسيب الجلسة محتاجة rollback، ورollback بيُنهي (expire) كل
            # كائنات الجلسة — أي وصول عادي (`booking.id`) بعدها بيحاول
            # lazy-load ضمني برّه سياق greenlet فيفشل بـMissingGreenlet
            # (خطأ ثانٍ بيطمس نجاح الحجز الفعلي ويرجّع 500 للعميل رغم أن
            # الحجز والدفع اتموا فعليًا). refresh() صريح (await حقيقي)
            # بيعيد تحميل الصف بأمان قبل أي وصول تاني [جلسة
            # transport-domain-full-build، 2026-09-01].
            await self.db.rollback()
            await self.db.refresh(booking)
            logger.error(f"Invoice creation failed for trip booking {booking.id}: {e}")

        # تخزين معرف الحجز فقط
        if idempotency_key:
            await self._store_idempotency(idempotency_key, {"booking_id": booking.id})

        return booking

    async def cancel_booking(self, tenant_id: int, booking_id: int, user_id: int) -> TripBooking:
        """يلغي حجزًا مؤكَّدًا قبل بدء الرحلة، ويحرر (release) الأجرة
        المحجوزة وقت الحجز — جزء من دورة hold_funds/settle/release الكاملة
        [قرار مستخدم، جلسة transport-domain-full-build، 2026-09-01]."""
        booking = await self.repo.get_booking(booking_id, tenant_id)
        if not booking:
            raise NotFoundError("Booking not found")
        if booking.passenger_id != user_id:  # type: ignore
            raise PermissionDeniedError("Not authorized to cancel this booking")
        if booking.status != "CONFIRMED":  # type: ignore
            raise ValueError("Booking cannot be cancelled in its current status")

        trip = await self.repo.get_trip(cast(int, booking.trip_id), tenant_id)  # type: ignore
        if not trip or trip.status != TripStatus.SCHEDULED:  # type: ignore
            raise ValueError("Trip has already started or completed — booking cannot be cancelled")

        finance = FinanceService(self.db, tenant_id)
        await finance.release_held_funds(
            user_id=user_id,
            amount=cast(Decimal, booking.fare_paid_mrusdt),  # type: ignore
            currency="MR_USDT",
            description=f"Booking {booking_id} cancelled",
            idempotency_key=f"RELEASE-BOOKING-{booking_id}",
        )

        result = await self.repo.cancel_booking(booking_id, tenant_id)

        await audit_log(  # type: ignore[call-arg]
            user_id=user_id,
            tenant_id=tenant_id,
            action="BOOKING_CANCELLED",
            resource_id=booking_id,
            details={"trip_id": booking.trip_id}  # type: ignore
        )
        await self.event_bus.publish("transport.booking.cancelled", {
            "booking_id": booking_id,
            "passenger_id": user_id,
            "tenant_id": tenant_id,
        })

        return cast(TripBooking, result)

    async def cancel_delivery(self, tenant_id: int, task_id: int, user_id: int) -> DeliveryTask:
        """يلغي مهمة توصيل لم تُسلَّم بعد، ويحرر (release) الرسوم المحجوزة
        لو كانت اتدفعت أصلًا عبر pay_delivery."""
        task = await self.repo.get_delivery_task(task_id, tenant_id)
        if not task:
            raise NotFoundError("Delivery task not found")
        if task.sender_id != user_id:  # type: ignore
            raise PermissionDeniedError("Not authorized to cancel this delivery")
        if task.status in ("DELIVERED", "CANCELLED"):  # type: ignore
            raise ValueError("Delivery cannot be cancelled in its current status")

        if task.payment_tx_hash:  # type: ignore
            finance = FinanceService(self.db, tenant_id)
            await finance.release_held_funds(
                user_id=user_id,
                amount=cast(Decimal, task.delivery_fee_mrusdt),  # type: ignore
                currency="MR_USDT",
                description=f"Delivery {task_id} cancelled",
                idempotency_key=f"RELEASE-DELIVERY-{task_id}",
            )

        result = await self.repo.cancel_delivery_task(task_id, tenant_id)

        await audit_log(  # type: ignore[call-arg]
            user_id=user_id,
            tenant_id=tenant_id,
            action="DELIVERY_CANCELLED",
            resource_id=task_id,
            details={}
        )
        await self.event_bus.publish("transport.delivery.cancelled", {
            "task_id": task_id,
            "sender_id": user_id,
            "tenant_id": tenant_id,
        })

        return cast(DeliveryTask, result)

    async def assign_delivery_to_trip(self, tenant_id: int, task_id: int, trip_id: int, user_id: int) -> DeliveryTask:
        task = await self.repo.get_delivery_task(task_id, tenant_id)
        if not task:
            raise NotFoundError("Delivery task not found")
        if task.sender_id != user_id:  # type: ignore
            raise PermissionDeniedError("Not authorized to assign this delivery")

        trip = await self.repo.get_trip(trip_id, tenant_id)
        if not trip:
            raise NotFoundError("Trip not found")

        result = await self.repo.assign_delivery_to_trip(task_id, tenant_id, trip_id)
        return cast(DeliveryTask, result)

    async def get_my_bookings(
        self,
        tenant_id: int,
        passenger_id: int
    ) -> List[TripBooking]:
        await self._check_saas_limits(tenant_id, "transport")
        result = await self.repo.list_bookings(tenant_id, passenger_id=passenger_id)
        return list(result)

    async def list_bookings(
        self,
        tenant_id: int,
        passenger_id: Optional[int] = None,
        trip_id: Optional[int] = None
    ) -> List[TripBooking]:
        result = await self.repo.list_bookings(tenant_id, passenger_id=passenger_id, trip_id=trip_id)
        return list(result)

    # ============================================================
    # 6. مهام التوصيل (Deliveries) – مع Idempotency محسّن
    # ============================================================
    async def create_delivery(
        self,
        tenant_id: int,
        sender_id: int,
        data: Dict[str, Any],
        idempotency_key: Optional[str] = None
    ) -> DeliveryTask:
        await self._check_saas_limits(tenant_id, "transport")

        # 1. التحقق من Idempotency
        if idempotency_key:
            cached = await self._validate_idempotency(idempotency_key)
            if cached is not None:
                task_id = cached.get("task_id")
                if task_id:
                    task = await self.repo.get_delivery_task(task_id, tenant_id)
                    if task:
                        return task
                raise ValidationError("Idempotency record exists but delivery task not found.")

        sanitized_pickup = self._sanitize_address(data["pickup_address"])
        sanitized_dropoff = self._sanitize_address(data["dropoff_address"])

        async with self.db.begin_nested():
            task = await self.repo.create_delivery_task(
                tenant_id=tenant_id,
                order_id=data.get("order_id"),
                sender_id=sender_id,
                receiver_id=data["receiver_id"],
                pickup_address=sanitized_pickup,
                dropoff_address=sanitized_dropoff,
                estimated_distance_km=data.get("estimated_distance_km"),
                delivery_fee_mrusdt=data.get("delivery_fee_mrusdt", Decimal(0)),
                status="PENDING",
                idempotency_key=idempotency_key
            )

            await audit_log(  # type: ignore[call-arg]
                user_id=sender_id,
                tenant_id=tenant_id,
                action="DELIVERY_CREATED",
                resource_id=task.id,
                details={"receiver_id": data["receiver_id"]}
            )

        await self.db.commit()

        # تخزين معرف المهمة فقط
        if idempotency_key:
            await self._store_idempotency(idempotency_key, {"task_id": task.id})

        return task

    async def get_delivery_task(self, task_id: int, tenant_id: int) -> DeliveryTask:
        task = await self.repo.get_delivery_task(task_id, tenant_id)
        if not task:
            raise NotFoundError("Delivery task not found")
        return task

    async def complete_delivery(
        self,
        tenant_id: int,
        task_id: int,
        driver_id: int,
        proof_hash: str
    ) -> DeliveryTask:
        await self._check_saas_limits(tenant_id, "transport")

        # فحص ملكية مستخدم — كان مفقودًا بالكامل (بس فحص تينانت)، أي
        # active_user من نفس التينانت كان يقدر ينهي أي توصيل [قرار مستخدم،
        # جلسة transport-domain-full-build، 2026-09-01]. المُنفِّذ الفعلي
        # لعملية التسليم هو سائق الرحلة المرتبطة — نفس نمط فحص driver_id
        # في start_trip/complete_trip فوق.
        task = await self.repo.get_delivery_task(task_id, tenant_id)
        if not task:
            raise NotFoundError("Delivery task not found")
        if not task.trip_id:  # type: ignore
            raise ValueError("Delivery not assigned to a trip")
        trip = await self.repo.get_trip(cast(int, task.trip_id), tenant_id)  # type: ignore
        if not trip or trip.driver_id != driver_id:  # type: ignore
            raise PermissionDeniedError("Not authorized to complete this delivery")

        # تسوية (settle) رسوم التوصيل المحجوزة (لو دُفعت أصلًا عبر
        # pay_delivery) — بتتحرر للسائق فعليًا دلوقتي بعد التسليم الفعلي.
        if task.payment_tx_hash:  # type: ignore
            driver = await self._get_user_by_id(driver_id, tenant_id)
            finance = FinanceService(self.db, tenant_id)
            try:
                await finance.settle_held_funds(
                    sender_id=cast(int, task.sender_id),  # type: ignore
                    receiver_email=cast(str, driver.email),
                    currency="MR_USDT",
                    amount=cast(Decimal, task.delivery_fee_mrusdt),  # type: ignore
                    notes=f"Delivery {task_id} completed",
                    idempotency_key=f"SETTLE-DELIVERY-{task_id}",
                )
            except Exception as e:
                logger.error(f"Settlement failed for delivery {task_id}: {e}")

        return await self.repo.complete_delivery(task_id, tenant_id, proof_hash)

    # ============================================================
    # 7. دفع رسوم التوصيل – مع Idempotency محسّن
    # ============================================================
    async def pay_delivery(
        self,
        tenant_id: int,
        task_id: int,
        payer_id: int,
        idempotency_key: Optional[str] = None
    ) -> DeliveryTask:
        await self._check_saas_limits(tenant_id, "transport")

        # 1. التحقق من Idempotency
        if idempotency_key:
            cached = await self._validate_idempotency(idempotency_key)
            if cached is not None:
                task_id_cached = cached.get("task_id")
                if task_id_cached:
                    task = await self.repo.get_delivery_task(task_id_cached, tenant_id)
                    if task:
                        return task
                raise ValidationError("Idempotency record exists but delivery task not found.")

        task = await self.repo.get_delivery_task(task_id, tenant_id)
        if not task or task.sender_id != payer_id:  # type: ignore
            raise NotFoundError("Delivery task not found")
        if task.payment_tx_hash:  # type: ignore
            raise ValueError("Already paid")
        if not task.trip_id:  # type: ignore
            raise ValueError("Delivery not assigned to a trip")

        trip = await self.repo.get_trip(task.trip_id, tenant_id)  # type: ignore
        if not trip:
            raise NotFoundError("Trip not found")
        driver = await self._get_user_by_id(cast(int, trip.driver_id), tenant_id)  # type: ignore

        finance = FinanceService(self.db, tenant_id)
        invoicing = InvoicingService(self.db, tenant_id)
        async with self.db.begin_nested():
            try:
                # حجز (hold) بدل تحويل مباشر — رسوم التوصيل بتتحرر للسائق
                # فقط لما التوصيل يكتمل فعليًا (complete_delivery)، أو
                # تترجع (release) لو اتلغى (cancel_delivery) [قرار مستخدم،
                # جلسة transport-domain-full-build، 2026-09-01].
                hold_tx = await finance.hold_funds(
                    user_id=payer_id,
                    amount=cast(Decimal, task.delivery_fee_mrusdt),  # type: ignore
                    currency="MR_USDT",
                    description=f"Delivery fee hold - task {task.id}",
                    idempotency_key=idempotency_key or ""
                )
            except InsufficientBalanceError:
                raise PermissionDeniedError("Insufficient balance")

            await self.db.execute(
                update(DeliveryTask).where(DeliveryTask.id == task_id).values(
                    payment_tx_hash=hold_tx.tx_hash
                )
            )

            await self._register_affiliate_commission(payer_id, tenant_id, cast(Decimal, task.delivery_fee_mrusdt))  # type: ignore

            await audit_log(  # type: ignore[call-arg]
                user_id=payer_id,
                tenant_id=tenant_id,
                action="DELIVERY_PAID",
                resource_id=task.id,
                details={"amount": float(cast(Decimal, task.delivery_fee_mrusdt))}  # type: ignore
            )

            await self.event_bus.publish("transport.delivery.paid", {
                "task_id": task.id,
                "payer_id": payer_id,
                "tenant_id": tenant_id
            })

        await self.db.commit()

        try:
            await invoicing.create_invoice(
                entity_id=tenant_id,
                user_id=payer_id,
                amount=cast(Decimal, task.delivery_fee_mrusdt),  # type: ignore
                description=f"Delivery task #{task.id}",
                due_date=datetime.utcnow() + timedelta(days=3)
            )
        except Exception as e:
            # نفس إصلاح book_trip فوق — rollback يُنهي (expire) كل كائنات
            # الجلسة، فأي وصول عادي لـtask.id بعده بيحتاج refresh() صريح
            # (await حقيقي) وإلا يفشل بـMissingGreenlet برّه سياق greenlet.
            await self.db.rollback()
            await self.db.refresh(task)
            logger.error(f"Invoice creation failed for delivery task {task.id}: {e}")

        # تخزين معرف المهمة فقط
        if idempotency_key:
            await self._store_idempotency(idempotency_key, {"task_id": task.id})

        return await self.repo.get_delivery_task(task_id, tenant_id)

    # ============================================================
    # 8. دوال مساعدة
    # ============================================================
    @staticmethod
    def calculate_carbon(vehicle: Vehicle, distance_km: float) -> float:
        return float(vehicle.carbon_per_km) * distance_km  # type: ignore

    async def _get_user_by_id(self, user_id: int, tenant_id: int) -> User:
        user = await self.user_repo.get_by_id(user_id, tenant_id)
        if not user:
            raise NotFoundError("User not found")
        return user

    async def _register_affiliate_commission(self, user_id: int, tenant_id: int, amount: Decimal):
        affiliate_service = AffiliateService(self.db, tenant_id)
        try:
            user = await self.user_repo.get_by_id(user_id, tenant_id)
            if user and user.referred_by_user_id:
                commission = amount * Decimal("0.02")
                scope_id = await affiliate_service.resolve_scope_id_for_member("TRANSPORT")
                if scope_id:
                    await affiliate_service.ensure_referral_link(user.referred_by_user_id, user_id, scope_id)
                    await affiliate_service.distribute_commissions_for_sale_event(
                        referred_user_id=user_id,
                        scope_id=scope_id,
                        sale_amount=commission,
                        source_type="TRANSPORT",
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

    def _sanitize_address(self, address: Dict[str, Any]) -> Dict[str, Any]:
        """تعقيم بيانات العنوان لمنع الهجمات."""
        if not isinstance(address, dict):
            return {}
        sanitized = {}
        for key, value in address.items():
            if isinstance(value, str):
                sanitized[key] = bleach.clean(value, tags=[], strip=True)
            elif isinstance(value, dict):
                sanitized[key] = self._sanitize_address(value)
            else:
                sanitized[key] = value
        return sanitized