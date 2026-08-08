import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.core.database import engine, AsyncSessionLocal # تأكد من اسم الـ Session لديك
from app.domains.identity.models import User

from app.domains.academy.models import AcademyTenant, OrganizationEntity
from dotenv import load_dotenv
load_dotenv()
async def seed_smart_tenant():
    print("⏳ جاري فحص وبناء الكيانات السيادية...")
    
    async with AsyncSessionLocal() as db:
        # 1. البحث عن السوبر أدمن (لربطه كمالك للأكاديمية)
        # نعتمد على الإيميل الموجود في ملف .env الخاص بك
        result = await db.execute(select(User).filter_by(email="admin@eppne.com"))
        admin = result.scalars().first()

        if not admin:
            print("❌ خطأ: لم يتم العثور على السوبر أدمن! يرجى التأكد من تشغيل سكربت زرع المستخدمين أولاً.")
            return

        # 2. النطاقات المطلوبة (نطاق التطوير ونطاق الإنتاج)
        domains_to_seed = [
            {"name": "EPPNE Local Academy", "domain": "localhost.com"},
            {"name": "EPPNE Sovereign Main", "domain": "eppne.com"}
        ]

        for target in domains_to_seed:
            # التحقق مما إذا كان النطاق موجوداً سلفاً
            tenant_result = await db.execute(select(AcademyTenant).filter_by(domain=target["domain"]))
            tenant = tenant_result.scalars().first()

            if not tenant:
                print(f"🌱 جاري زرع أكاديمية للنطاق: {target['domain']}...")
                tenant = AcademyTenant(
                    name=target["name"],
                    domain=target["domain"],
                    admin_id=admin.id,
                    is_active=True
                )
                db.add(tenant)
                await db.flush() # للحصول على tenant.id فوراً دون إغلاق الجلسة
                print(f"✅ تم إنشاء المستأجر بنجاح (ID: {tenant.id})")
            else:
                print(f"⚡ الأكاديمية للنطاق {target['domain']} موجودة ومستقرة (ID: {tenant.id}).")

            # 3. بناء الكيان التنظيمي الجذري (الشجرة السيادية)
            org_result = await db.execute(
                select(OrganizationEntity).filter_by(tenant_id=tenant.id, parent_id=None)
            )
            root_org = org_result.scalars().first()

            if not root_org:
                print(f"🏗️ جاري بناء القيادة العليا لأكاديمية {target['name']}...")
                root_org = OrganizationEntity(
                    tenant_id=tenant.id,
                    name=f"القيادة العليا - {target['name']}",
                    entity_type="HEADQUARTERS",
                    description="الكيان السيادي الرئيسي لإدارة الأكاديمية وفروعها",
                    is_active=True
                )
                db.add(root_org)
                print("✅ تم بناء الهيكل التنظيمي بنجاح.")

        # حفظ كل التغييرات بضربة واحدة آمنة
        await db.commit()
        print("🚀 اكتملت عملية التأسيس السيادي بنجاح! المنصة جاهزة.")

if __name__ == "__main__":
    asyncio.run(seed_smart_tenant())