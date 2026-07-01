import asyncio
from sqlalchemy import text
from app.core.database import engine

async def seed_tenant():
    print("⏳ جاري الاتصال بقاعدة البيانات لزرع الكيان الأساسي...")
    async with engine.begin() as conn:
        await conn.execute(text("""
            INSERT INTO academy_tenants (id, name, domain, admin_id) 
            VALUES (1, 'EPPNE Sovereign Main', 'eppne.com', 1)
            ON CONFLICT (id) DO NOTHING;
        """))
    print("✅ تم زرع الكيان الأساسي (Tenant ID: 1) بنجاح!")
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(seed_tenant())