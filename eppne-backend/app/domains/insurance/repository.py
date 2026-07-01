"""
مستودع قطاع التأمينات السيادية
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func, and_, or_
from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal  # <-- إضافة هذا السطر

from app.domains.insurance.models import (
    InsurancePolicy, InsuranceSubscription, InsuranceClaim,
    PensionRecord, EmployeeInsuranceProfile,
    ClaimStatus, PensionStatus, PolicyType  # <-- إضافة PolicyType هنا
)
from app.core.errors import NotFoundError

class InsuranceRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ========== Policies ==========
    async def create_policy(self, **kwargs) -> InsurancePolicy:
        policy = InsurancePolicy(**kwargs)
        self.db.add(policy)
        await self.db.commit()
        await self.db.refresh(policy)
        return policy

    async def get_policy(self, policy_id: int) -> Optional[InsurancePolicy]:
        result = await self.db.execute(
            select(InsurancePolicy).where(InsurancePolicy.id == policy_id, InsurancePolicy.is_deleted == False)
        )
        return result.scalar_one_or_none()

    async def list_policies(
        self,
        tenant_id: int,
        policy_type: Optional[PolicyType] = None,
        is_active: Optional[bool] = None,
        skip: int = 0,
        limit: int = 50
    ) -> List[InsurancePolicy]:
        query = select(InsurancePolicy).where(InsurancePolicy.tenant_id == tenant_id, InsurancePolicy.is_deleted == False)
        if policy_type:
            query = query.where(InsurancePolicy.policy_type == policy_type)
        if is_active is not None:
            query = query.where(InsurancePolicy.is_active == is_active)
        query = query.order_by(InsurancePolicy.created_at.desc()).offset(skip).limit(limit)
        result = await self.db.execute(query)
        return result.scalars().all()

    async def update_policy(self, policy_id: int, **kwargs) -> InsurancePolicy:
        await self.db.execute(update(InsurancePolicy).where(InsurancePolicy.id == policy_id).values(**kwargs))
        await self.db.commit()
        return await self.get_policy(policy_id)

    # ========== Subscriptions ==========
    async def create_subscription(self, **kwargs) -> InsuranceSubscription:
        sub = InsuranceSubscription(**kwargs)
        self.db.add(sub)
        await self.db.commit()
        await self.db.refresh(sub)
        return sub

    async def get_subscription(self, subscription_id: int) -> Optional[InsuranceSubscription]:
        result = await self.db.execute(select(InsuranceSubscription).where(InsuranceSubscription.id == subscription_id))
        return result.scalar_one_or_none()

    async def list_subscriptions(
        self,
        tenant_id: int,
        user_id: Optional[int] = None,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 50
    ) -> List[InsuranceSubscription]:
        # نحتاج tenant_id من policy
        query = select(InsuranceSubscription).join(
            InsurancePolicy, InsuranceSubscription.policy_id == InsurancePolicy.id
        ).where(InsurancePolicy.tenant_id == tenant_id)
        if user_id:
            query = query.where(InsuranceSubscription.subscriber_user_id == user_id)
        if status:
            query = query.where(InsuranceSubscription.status == status)
        query = query.order_by(InsuranceSubscription.created_at.desc()).offset(skip).limit(limit)
        result = await self.db.execute(query)
        return result.scalars().all()

    async def update_subscription(self, subscription_id: int, **kwargs) -> InsuranceSubscription:
        await self.db.execute(update(InsuranceSubscription).where(InsuranceSubscription.id == subscription_id).values(**kwargs))
        await self.db.commit()
        return await self.get_subscription(subscription_id)

    # ========== Claims ==========
    async def create_claim(self, **kwargs) -> InsuranceClaim:
        claim = InsuranceClaim(**kwargs)
        self.db.add(claim)
        await self.db.commit()
        await self.db.refresh(claim)
        return claim

    async def get_claim(self, claim_id: int) -> Optional[InsuranceClaim]:
        result = await self.db.execute(select(InsuranceClaim).where(InsuranceClaim.id == claim_id))
        return result.scalar_one_or_none()

    async def list_claims_for_subscription(self, subscription_id: int) -> List[InsuranceClaim]:
        result = await self.db.execute(
            select(InsuranceClaim).where(InsuranceClaim.subscription_id == subscription_id)
            .order_by(InsuranceClaim.created_at.desc())
        )
        return result.scalars().all()

    async def list_claims_for_user(self, user_id: int, status: Optional[ClaimStatus] = None) -> List[InsuranceClaim]:
        query = select(InsuranceClaim).where(InsuranceClaim.claimant_user_id == user_id)
        if status:
            query = query.where(InsuranceClaim.status == status)
        query = query.order_by(InsuranceClaim.created_at.desc())
        result = await self.db.execute(query)
        return result.scalars().all()

    async def update_claim(self, claim_id: int, **kwargs) -> InsuranceClaim:
        await self.db.execute(update(InsuranceClaim).where(InsuranceClaim.id == claim_id).values(**kwargs))
        await self.db.commit()
        return await self.get_claim(claim_id)

    # ========== Pensions ==========
    async def create_pension(self, **kwargs) -> PensionRecord:
        pension = PensionRecord(**kwargs)
        self.db.add(pension)
        await self.db.commit()
        await self.db.refresh(pension)
        return pension

    async def get_pension(self, pension_id: int) -> Optional[PensionRecord]:
        result = await self.db.execute(select(PensionRecord).where(PensionRecord.id == pension_id))
        return result.scalar_one_or_none()

    async def list_pensions_for_beneficiary(self, beneficiary_id: int, status: Optional[PensionStatus] = None) -> List[PensionRecord]:
        query = select(PensionRecord).where(PensionRecord.beneficiary_id == beneficiary_id)
        if status:
            query = query.where(PensionRecord.status == status)
        query = query.order_by(PensionRecord.start_date.desc())
        result = await self.db.execute(query)
        return result.scalars().all()

    async def update_pension(self, pension_id: int, **kwargs) -> PensionRecord:
        await self.db.execute(update(PensionRecord).where(PensionRecord.id == pension_id).values(**kwargs))
        await self.db.commit()
        return await self.get_pension(pension_id)

    # ========== Employee Insurance Profiles ==========
    async def create_employee_profile(self, **kwargs) -> EmployeeInsuranceProfile:
        profile = EmployeeInsuranceProfile(**kwargs)
        self.db.add(profile)
        await self.db.commit()
        await self.db.refresh(profile)
        return profile

    async def get_employee_profile(self, user_id: int) -> Optional[EmployeeInsuranceProfile]:
        result = await self.db.execute(select(EmployeeInsuranceProfile).where(EmployeeInsuranceProfile.user_id == user_id))
        return result.scalar_one_or_none()

    async def update_employee_profile(self, user_id: int, **kwargs) -> EmployeeInsuranceProfile:
        await self.db.execute(update(EmployeeInsuranceProfile).where(EmployeeInsuranceProfile.user_id == user_id).values(**kwargs))
        await self.db.commit()
        return await self.get_employee_profile(user_id)

    async def add_contribution(self, user_id: int, amount: Decimal) -> EmployeeInsuranceProfile:
        profile = await self.get_employee_profile(user_id)
        if profile:
            profile.total_contributed_mrusdt += amount
            profile.last_contribution_date = func.now()
            await self.db.commit()
            await self.db.refresh(profile)
        return profile