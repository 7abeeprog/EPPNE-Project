# app/domains/manufacturing/repository.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func
from typing import Optional, List, Dict, Any, cast
from app.domains.manufacturing.models import *
from app.core.errors import NotFoundError
from decimal import Decimal
from datetime import datetime


class ManufacturingRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ============================================================
    # المنشآت (Facilities)
    # ============================================================

    async def create_facility(self, **kwargs) -> ManufacturingFacility:
        facility = ManufacturingFacility(**kwargs)
        self.db.add(facility)
        await self.db.commit()
        await self.db.refresh(facility)
        return facility

    async def get_facility(self, facility_id: int, tenant_id: int) -> Optional[ManufacturingFacility]:
        result = await self.db.execute(
            select(ManufacturingFacility).where(
                ManufacturingFacility.id == facility_id,  # type: ignore
                ManufacturingFacility.tenant_id == tenant_id,  # type: ignore
                ManufacturingFacility.is_deleted == False  # type: ignore
            )
        )
        return result.scalar_one_or_none()

    async def list_facilities(self, tenant_id: int, skip: int = 0, limit: int = 50) -> List[ManufacturingFacility]:
        result = await self.db.execute(
            select(ManufacturingFacility).where(
                ManufacturingFacility.tenant_id == tenant_id,  # type: ignore
                ManufacturingFacility.is_deleted == False  # type: ignore
            ).order_by(ManufacturingFacility.created_at.desc()).offset(skip).limit(limit)  # type: ignore
        )
        return list(result.scalars().all())  # ✅ تحويل إلى List

    # ============================================================
    # خطوط الإنتاج (Production Lines)
    # ============================================================

    async def create_production_line(self, **kwargs) -> ProductionLine:
        line = ProductionLine(**kwargs)
        self.db.add(line)
        await self.db.commit()
        await self.db.refresh(line)
        return line

    async def get_production_line(self, line_id: int, tenant_id: int) -> Optional[ProductionLine]:
        result = await self.db.execute(
            select(ProductionLine)
            .join(ManufacturingFacility, ProductionLine.facility_id == ManufacturingFacility.id)
            .where(
                ProductionLine.id == line_id,  # type: ignore
                ManufacturingFacility.tenant_id == tenant_id  # type: ignore
            )
        )
        return result.scalar_one_or_none()

    # ============================================================
    # النماذج (Blueprints)
    # ============================================================

    async def create_blueprint(self, **kwargs) -> ProductBlueprint:
        bp = ProductBlueprint(**kwargs)
        self.db.add(bp)
        await self.db.commit()
        await self.db.refresh(bp)
        return bp

    async def get_blueprint(self, blueprint_id: int, tenant_id: int) -> Optional[ProductBlueprint]:
        result = await self.db.execute(
            select(ProductBlueprint).where(
                ProductBlueprint.id == blueprint_id,  # type: ignore
                ProductBlueprint.tenant_id == tenant_id  # type: ignore
            )
        )
        return result.scalar_one_or_none()

    # ============================================================
    # دفعات الإنتاج (Production Batches)
    # ============================================================

    async def create_batch(self, **kwargs) -> ProductionBatch:
        batch = ProductionBatch(**kwargs)
        self.db.add(batch)
        await self.db.commit()
        await self.db.refresh(batch)
        return batch

    async def get_batch(self, batch_id: int, tenant_id: int) -> Optional[ProductionBatch]:
        result = await self.db.execute(
            select(ProductionBatch)
            .join(ProductBlueprint, ProductionBatch.product_blueprint_id == ProductBlueprint.id)
            .where(
                ProductionBatch.id == batch_id,  # type: ignore
                ProductBlueprint.tenant_id == tenant_id  # type: ignore
            )
        )
        return result.scalar_one_or_none()

    async def update_batch_status(
        self,
        batch_id: int,
        status: ProductionStatus,
        produced_quantity: Optional[int] = None,
        notes: Optional[str] = None
    ) -> ProductionBatch:
        values: Dict[str, Any] = {"status": status}  # ✅ تحديد النوع صراحةً
        if produced_quantity is not None:
            values["produced_quantity"] = produced_quantity
        if notes is not None:
            values["quality_control_notes"] = notes
        await self.db.execute(update(ProductionBatch).where(ProductionBatch.id == batch_id).values(**values))  # type: ignore
        await self.db.commit()
        return await self.get_batch(batch_id, 1)  # tenant_id سيتم تمريره من Service

    # ============================================================
    # المنتجات الذكية (Smart Product Items)
    # ============================================================

    async def bulk_create_items(self, items: List[SmartProductItem]) -> List[SmartProductItem]:
        self.db.add_all(items)
        await self.db.commit()
        for item in items:
            await self.db.refresh(item)
        return items

    async def get_item(self, item_id: int, tenant_id: int) -> Optional[SmartProductItem]:
        result = await self.db.execute(
            select(SmartProductItem)
            .join(ProductionBatch, SmartProductItem.batch_id == ProductionBatch.id)
            .join(ProductBlueprint, ProductionBatch.product_blueprint_id == ProductBlueprint.id)
            .where(
                SmartProductItem.id == item_id,  # type: ignore
                ProductBlueprint.tenant_id == tenant_id  # type: ignore
            )
        )
        return result.scalar_one_or_none()

    async def update_item(self, item_id: int, **kwargs) -> SmartProductItem:
        await self.db.execute(update(SmartProductItem).where(SmartProductItem.id == item_id).values(**kwargs))  # type: ignore
        await self.db.commit()
        result = await self.db.execute(select(SmartProductItem).where(SmartProductItem.id == item_id))  # type: ignore
        return result.scalar_one()

    async def list_batch_items(self, batch_id: int) -> List[SmartProductItem]:
        result = await self.db.execute(select(SmartProductItem).where(SmartProductItem.batch_id == batch_id))  # type: ignore
        return list(result.scalars().all())  # ✅ تحويل إلى List

    # ============================================================
    # المواد الخام (Raw Materials)
    # ============================================================

    async def create_raw_material_batch(self, **kwargs) -> RawMaterialBatch:
        batch = RawMaterialBatch(**kwargs)
        self.db.add(batch)
        await self.db.commit()
        await self.db.refresh(batch)
        return batch

    async def get_raw_material_batch(self, batch_id: int, tenant_id: int) -> Optional[RawMaterialBatch]:
        result = await self.db.execute(
            select(RawMaterialBatch).where(
                RawMaterialBatch.id == batch_id,  # type: ignore
                RawMaterialBatch.tenant_id == tenant_id,  # type: ignore
                RawMaterialBatch.is_deleted == False  # type: ignore
            )
        )
        return result.scalar_one_or_none()

    async def list_raw_materials(self, tenant_id: int, skip: int = 0, limit: int = 100) -> List[RawMaterialBatch]:
        result = await self.db.execute(
            select(RawMaterialBatch).where(
                RawMaterialBatch.tenant_id == tenant_id,  # type: ignore
                RawMaterialBatch.is_deleted == False  # type: ignore
            ).order_by(RawMaterialBatch.received_date.desc()).offset(skip).limit(limit)  # type: ignore
        )
        return list(result.scalars().all())  # ✅ تحويل إلى List

    async def update_raw_material_batch(self, batch_id: int, **kwargs) -> RawMaterialBatch:
        await self.db.execute(update(RawMaterialBatch).where(RawMaterialBatch.id == batch_id).values(**kwargs))  # type: ignore
        await self.db.commit()
        return await self.get_raw_material_batch(batch_id, 1)  # tenant_id سيتم تمريره من Service

    async def consume_material(self, **kwargs) -> MaterialConsumptionLog:
        log = MaterialConsumptionLog(**kwargs)
        self.db.add(log)
        await self.db.commit()
        await self.db.refresh(log)
        return log

    # ============================================================
    # التوأم الرقمي (Digital Twin)
    # ============================================================

    async def create_digital_twin(self, **kwargs) -> ProductDigitalTwin:
        twin = ProductDigitalTwin(**kwargs)
        self.db.add(twin)
        await self.db.commit()
        await self.db.refresh(twin)
        return twin

    async def get_digital_twin(self, product_item_id: int, tenant_id: int) -> Optional[ProductDigitalTwin]:
        result = await self.db.execute(
            select(ProductDigitalTwin)
            .join(SmartProductItem, ProductDigitalTwin.product_item_id == SmartProductItem.id)
            .join(ProductionBatch, SmartProductItem.batch_id == ProductionBatch.id)
            .join(ProductBlueprint, ProductionBatch.product_blueprint_id == ProductBlueprint.id)
            .where(
                ProductDigitalTwin.product_item_id == product_item_id,  # type: ignore
                ProductBlueprint.tenant_id == tenant_id  # type: ignore
            )
        )
        return result.scalar_one_or_none()

    async def get_digital_twin_by_id(self, twin_id: int) -> Optional[ProductDigitalTwin]:
        result = await self.db.execute(select(ProductDigitalTwin).where(ProductDigitalTwin.id == twin_id))  # type: ignore
        return result.scalar_one_or_none()

    async def update_digital_twin_maintenance(self, twin_id: int, maintenance_event: dict, cost: Decimal) -> ProductDigitalTwin:
        twin = await self.get_digital_twin_by_id(twin_id)
        if twin:
            maintenance_log = twin.maintenance_log or []  # type: ignore
            maintenance_log.append(maintenance_event)
            twin.maintenance_log = maintenance_log  # type: ignore
            twin.total_maintenance_cost_mrusdt += cost  # type: ignore
            await self.db.commit()
            await self.db.refresh(twin)
        return twin

    # ============================================================
    # شهادات الجودة (Quality Certificates)
    # ============================================================

    async def create_quality_certificate(self, **kwargs) -> QualityCertificate:
        cert = QualityCertificate(**kwargs)
        self.db.add(cert)
        await self.db.commit()
        await self.db.refresh(cert)
        return cert

    async def get_certificates_for_entity(self, entity_type: str, entity_id: int, tenant_id: int) -> List[QualityCertificate]:
        result = await self.db.execute(
            select(QualityCertificate).where(
                QualityCertificate.certified_entity_type == entity_type,  # type: ignore
                QualityCertificate.certified_entity_id == entity_id,  # type: ignore
                QualityCertificate.tenant_id == tenant_id,  # type: ignore
                QualityCertificate.is_deleted == False  # type: ignore
            )
        )
        return list(result.scalars().all())  # ✅ تحويل إلى List

    # ============================================================
    # الصيانة التنبؤية (Predictive Maintenance)
    # ============================================================

    async def create_predictive_log(self, **kwargs) -> PredictiveMaintenanceLog:
        log = PredictiveMaintenanceLog(**kwargs)
        self.db.add(log)
        await self.db.commit()
        await self.db.refresh(log)
        return log

    async def get_pending_maintenance(self, production_line_id: int, tenant_id: int) -> List[PredictiveMaintenanceLog]:
        result = await self.db.execute(
            select(PredictiveMaintenanceLog)
            .join(ProductionLine, PredictiveMaintenanceLog.production_line_id == ProductionLine.id)
            .join(ManufacturingFacility, ProductionLine.facility_id == ManufacturingFacility.id)
            .where(
                PredictiveMaintenanceLog.production_line_id == production_line_id,  # type: ignore
                PredictiveMaintenanceLog.status == "PENDING",  # type: ignore
                ManufacturingFacility.tenant_id == tenant_id  # type: ignore
            )
        )
        return list(result.scalars().all())  # ✅ تحويل إلى List

    async def schedule_maintenance(self, log_id: int, scheduled_at: datetime) -> PredictiveMaintenanceLog:
        await self.db.execute(
            update(PredictiveMaintenanceLog).where(PredictiveMaintenanceLog.id == log_id).values(  # type: ignore
                status="SCHEDULED", maintenance_scheduled_at=scheduled_at
            )
        )
        await self.db.commit()
        result = await self.db.execute(select(PredictiveMaintenanceLog).where(PredictiveMaintenanceLog.id == log_id))  # type: ignore
        return result.scalar_one()

    # ============================================================
    # قطع الغيار (Spare Parts)
    # ============================================================

    async def create_spare_part(self, **kwargs) -> SparePart:
        part = SparePart(**kwargs)
        self.db.add(part)
        await self.db.commit()
        await self.db.refresh(part)
        return part

    async def get_spare_part(self, part_id: int, tenant_id: int) -> Optional[SparePart]:
        result = await self.db.execute(
            select(SparePart).where(
                SparePart.id == part_id,  # type: ignore
                SparePart.tenant_id == tenant_id,  # type: ignore
                SparePart.is_deleted == False  # type: ignore
            )
        )
        return result.scalar_one_or_none()

    async def list_spare_parts(self, tenant_id: int, skip: int = 0, limit: int = 100) -> List[SparePart]:
        result = await self.db.execute(
            select(SparePart).where(
                SparePart.tenant_id == tenant_id,  # type: ignore
                SparePart.is_deleted == False  # type: ignore
            ).order_by(SparePart.created_at.desc()).offset(skip).limit(limit)  # type: ignore
        )
        return list(result.scalars().all())  # ✅ تحويل إلى List

    async def update_spare_part_stock(self, part_id: int, quantity_delta: int) -> SparePart:
        part = await self.get_spare_part(part_id, 1)  # tenant_id سيتم تمريره من Service
        if part:
            part.stock_quantity += quantity_delta  # type: ignore
            if quantity_delta > 0:
                part.last_restocked_at = func.now()  # type: ignore
            await self.db.commit()
            await self.db.refresh(part)
        return part