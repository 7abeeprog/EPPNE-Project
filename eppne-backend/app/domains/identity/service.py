# app/domains/identity/service.py
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, Dict
import uuid

from app.domains.identity.repository import UserRepository, WalletRepository
from app.domains.identity.models import User, Wallet
from app.domains.identity.schemas import UserCreate, UserUpdate
from app.core.security import get_password_hash, verify_password
from app.domains.auth.jwt_service import create_access_token, create_refresh_token, verify_refresh_token, revoke_refresh_token
from app.core.errors import PermissionDeniedError, NotFoundError, ValidationError
from app.core.logging_conf import logger

class UserService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.user_repo = UserRepository(db)
        self.wallet_repo = WalletRepository(db)

    # ==========================================
    # 1. التسجيل (مع Idempotency Key)
    # ==========================================
    async def register(self, data: UserCreate, idempotency_key: Optional[str] = None) -> User:
        """
        ✅ إنشاء مستخدم جديد مع التحقق من Idempotency Key.
        ✅ إنشاء محفظة تلقائياً للمستخدم الجديد.
        """
        # ✅ التحقق من Idempotency Key (منع التكرار)
        if idempotency_key:
            existing_user = await self.user_repo.get_by_idempotency_key(idempotency_key)
            if existing_user:
                logger.info(f"Duplicate registration blocked: {idempotency_key}")
                return existing_user

        # التحقق من عدم وجود البريد أو اسم المستخدم
        existing = await self.user_repo.get_by_email(data.email)
        if existing:
            raise ValidationError("البريد الإلكتروني مسجل بالفعل")
        existing = await self.user_repo.get_by_username(data.username)
        if existing:
            raise ValidationError("اسم المستخدم مستخدم بالفعل")

        # تشفير كلمة المرور
        hashed = get_password_hash(data.password.get_secret_value())

        # إنشاء المستخدم (بدون balances)
        user = User(
            username=data.username,
            email=data.email,
            hashed_password=hashed,
            name_ar=data.name_ar,
            name_en=data.name_en,
            birth_date=data.birth_date,
            marriage_status=data.marriage_status,
            language_preference=data.language_preference,
            profile_metadata=data.profile_metadata or {},
            preferences=data.preferences or {},
            public_id=str(uuid.uuid4()),
        )
        user = await self.user_repo.create(user)

        # ✅ إنشاء المحفظة تلقائياً
        await self.wallet_repo.create(user.id)

        return user

    # ==========================================
    # 2. المصادقة (مع تحديث آخر تسجيل دخول)
    # ==========================================
    async def authenticate(self, username_or_email: str, password: str, ip: Optional[str] = None, user_agent: Optional[str] = None) -> Optional[User]:
        user = await self.user_repo.get_by_username_or_email(username_or_email)
        if not user:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        if not user.is_active:
            return None

        # ✅ تحديث آخر تسجيل دخول
        await self.user_repo.update(
            user.id,
            last_login_at=func.now(),
            last_login_ip=ip,
            last_login_user_agent=user_agent
        )

        return user

    # ==========================================
    # 3. توليد التوكنات (مع Session Version)
    # ==========================================
    async def generate_tokens(self, user: User) -> Dict[str, str]:
        access_token = create_access_token(
            data={
                "sub": str(user.id),
                "role": user.system_role.value,
                "sv": user.session_version
            }
        )
        refresh_token = create_refresh_token(
            data={
                "sub": str(user.id),
                "sv": user.session_version
            }
        )
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer"
        }

    # ==========================================
    # 4. تجديد التوكنات (مع Token Rotation)
    # ==========================================
    async def refresh_tokens(self, refresh_token: str) -> Dict[str, str]:
        """
        ✅ تنفيذ Refresh Token Rotation.
        ✅ يتم إبطال التوكن القديم وإنشاء توكن جديد.
        """
        # التحقق من صحة التوكن
        payload = verify_refresh_token(refresh_token)
        if not payload:
            raise PermissionDeniedError("انتهت صلاحية الجلسة")

        user_id = int(payload.get("sub"))
        session_version = payload.get("sv")

        # جلب المستخدم مع صلاحية المحفظة
        user = await self.user_repo.get_by_id(user_id, load_wallet=True)
        if not user or not user.is_active:
            raise PermissionDeniedError("المستخدم غير نشط")

        # التحقق من session_version
        if user.session_version != session_version:
            raise PermissionDeniedError("تم إبطال الجلسة من مكان آخر")

        # ✅ إبطال التوكن القديم (Token Rotation)
        await revoke_refresh_token(refresh_token)

        # ✅ إنشاء توكنات جديدة مع session_version الحالي
        new_access_token = create_access_token(
            data={
                "sub": str(user.id),
                "role": user.system_role.value,
                "sv": user.session_version
            }
        )
        new_refresh_token = create_refresh_token(
            data={
                "sub": str(user.id),
                "sv": user.session_version
            }
        )

        return {
            "access_token": new_access_token,
            "refresh_token": new_refresh_token,
            "token_type": "bearer"
        }

    # ==========================================
    # 5. إبطال جميع الجلسات
    # ==========================================
    async def revoke_all_sessions(self, user_id: int) -> int:
        """✅ إبطال جميع جلسات المستخدم (زيادة session_version)"""
        # زيادة session_version
        await self.user_repo.update(user_id, session_version=User.session_version + 1)
        # إبطال جميع Refresh Tokens
        revoked_count = await revoke_all_user_tokens(user_id)
        return revoked_count

    # ==========================================
    # 6. دوال أخرى
    # ==========================================
    async def get_user(self, user_id: int) -> User:
        user = await self.user_repo.get_by_id(user_id, load_wallet=True)
        if not user:
            raise NotFoundError("المستخدم غير موجود")
        return user

    async def update_user(self, user_id: int, data: UserUpdate) -> User:
        update_data = data.model_dump(exclude_unset=True)
        forbidden = {"id", "public_id", "hashed_password", "system_role", "sovereign_rank"}
        for f in forbidden:
            update_data.pop(f, None)
        user = await self.user_repo.update(user_id, **update_data)
        if not user:
            raise NotFoundError("المستخدم غير موجود")
        return user

    async def change_password(self, user_id: int, old_password: str, new_password: str) -> bool:
        user = await self.user_repo.get_by_id(user_id)
        if not user or not verify_password(old_password, user.hashed_password):
            raise PermissionDeniedError("كلمة المرور الحالية غير صحيحة")
        new_hashed = get_password_hash(new_password)
        await self.user_repo.update(user_id, hashed_password=new_hashed)
        return True

    async def link_wallet(self, user_id: int, wallet_address: str, signature_proof: str) -> bool:
        await self.user_repo.update(user_id, primary_wallet=wallet_address)
        return True