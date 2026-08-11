# app/domains/identity/invitation_service.py
import secrets
from typing import Optional, List, Tuple
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.identity.repository import InvitationRepository
from app.domains.identity.models import TenantInvitation, User
from app.domains.identity.schemas import TenantInvitationCreate, InvitationRegisterRequest
from app.domains.identity.service import UserService
from app.core.errors import NotFoundError, PermissionDeniedError, ValidationError


class InvitationService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = InvitationRepository(db)

    async def create_invitation(
        self, referrer_user_id: int, tenant_id: int, data: TenantInvitationCreate
    ) -> Tuple[TenantInvitation, str]:
        token = secrets.token_urlsafe(32)
        invitation = await self.repo.create(
            tenant_id=tenant_id,
            referrer_user_id=referrer_user_id,
            token=token,
            email=data.email,
            product_id=data.product_id,
            max_uses=data.max_uses,
            expires_at=data.expires_at,
        )
        return invitation, token

    async def list_mine(self, referrer_user_id: int, tenant_id: int, skip: int = 0, limit: int = 20) -> List[TenantInvitation]:
        return await self.repo.list_by_referrer(referrer_user_id, tenant_id, skip, limit)

    async def list_tenant(self, tenant_id: int, skip: int = 0, limit: int = 20) -> List[TenantInvitation]:
        return await self.repo.list_by_tenant(tenant_id, skip, limit)

    async def get_one(self, invitation_id: int, tenant_id: int, current_user_id: int, is_admin: bool) -> TenantInvitation:
        invitation = await self.repo.get_by_id(invitation_id, tenant_id)
        if not invitation:
            raise NotFoundError("الدعوة غير موجودة")
        if invitation.referrer_user_id != current_user_id and not is_admin:
            raise PermissionDeniedError("غير مصرح بعرض هذه الدعوة")
        return invitation

    async def revoke(self, invitation_id: int, tenant_id: int, current_user_id: int, is_admin: bool) -> TenantInvitation:
        invitation = await self.repo.get_by_id(invitation_id, tenant_id)
        if not invitation:
            raise NotFoundError("الدعوة غير موجودة")
        if invitation.referrer_user_id != current_user_id and not is_admin:
            raise PermissionDeniedError("غير مصرح بإبطال هذه الدعوة")
        result = await self.repo.revoke(invitation_id, tenant_id, current_user_id)
        if not result:
            raise NotFoundError("الدعوة غير موجودة")
        return result

    async def register_with_invitation(self, data: InvitationRegisterRequest, idempotency_key: Optional[str] = None) -> User:
        invitation = await self.repo.get_by_token(data.token)
        if not invitation:
            raise NotFoundError("دعوة غير صالحة")

        if not invitation.is_active_now():
            raise ValidationError("الدعوة غير صالحة أو منتهية أو مستنفدة")

        if invitation.email and data.email.lower() != invitation.email.lower():
            raise ValidationError("البريد الإلكتروني لا يطابق الدعوة")

        claimed = await self.repo.claim_use(invitation.id)
        if not claimed:
            raise ValidationError("الدعوة غير متاحة")

        try:
            user = await UserService(self.db, invitation.tenant_id).register(data, idempotency_key)
        except Exception:
            await self.repo.release_use(invitation.id)
            raise

        await self.repo.finalize_if_exhausted(invitation.id)
        return user
