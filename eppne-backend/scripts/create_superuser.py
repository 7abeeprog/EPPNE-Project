import os
from dotenv import load_dotenv

# تحميل متغيرات البيئة قبل أي استدعاء آخر
load_dotenv()

# باقي استدعاءات الملف الطبيعية
import asyncio
from app.core.database import AsyncSessionLocal
from app.core.config import settings
# ... (باقي الكود كما هو)
from sqlalchemy.ext.asyncio import AsyncSession
from app.domains.identity.models import User
from app.core.enums import SystemRole, SovereignRank, KYCStatus
from app.core.security import get_password_hash
from sqlalchemy import select

async def create_superuser():
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.email == settings.FIRST_SUPERUSER_EMAIL))
        user = result.scalar_one_or_none()
        if user:
            print("Superuser already exists.")
            return

        new_user = User(
            username=settings.FIRST_SUPERUSER_USERNAME,
            email=settings.FIRST_SUPERUSER_EMAIL,
            hashed_password=get_password_hash(settings.FIRST_SUPERUSER_PASSWORD),
            name_ar=settings.FIRST_SUPERUSER_NAME_AR,
            name_en=settings.FIRST_SUPERUSER_NAME_EN,
            system_role=SystemRole.EXECUTIVE_DIRECTOR,
            sovereign_rank=SovereignRank.FOUNDER_L7,
            kyc_status=KYCStatus.VERIFIED,
            is_active=True,
            balances={"MR_POUND": 1000000, "MR_USDT": 1000000, "MR7": 1000000, "NBT": 10000, "MRX": 1000}
        )
        db.add(new_user)
        await db.commit()
        print(f"Superuser created: {settings.FIRST_SUPERUSER_EMAIL}")

if __name__ == "__main__":
    asyncio.run(create_superuser())