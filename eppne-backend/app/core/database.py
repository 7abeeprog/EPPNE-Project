# app/core/database.py
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from app.core.config import settings

# ==========================================
# 1. إعداد محرك قاعدة البيانات (Database Engine)
# ==========================================
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,  # اجعلها True في بيئة التطوير لو أردت رؤية أوامر SQL في الترمينال
    pool_size=getattr(settings, "DATABASE_POOL_SIZE", 20),   # استخدام 20 كقيمة احتياطية
    max_overflow=getattr(settings, "DATABASE_MAX_OVERFLOW", 10),  # استخدام 10 كقيمة احتياطية
    pool_timeout=60,  # ✅ إضافة 60 ثانية كوقت انتظار لتجنب أخطاء الـ Timeout
    pool_pre_ping=True,  # لضمان التحقق من صحة الاتصال قبل تنفيذه (يمنع أخطاء الاتصالات الميتة)
)

# ==========================================
# 2. مصنع الجلسات (Session Maker)
# ==========================================
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False
)

# أضف هذا السطر ليكون الاسم متاحاً عالمياً في المشروع
SessionLocal = AsyncSessionLocal

# ==========================================
# 3. الفئة الأساسية للموديلات (Base Model)
# ==========================================
Base = declarative_base()

# ==========================================
# 4. دالة حقن التبعية (Dependency Injection)
# ==========================================
async def get_db():
    """يُستخدم لحقن الجلسة في مسارات الـ API وإغلاقها بأمان بعد انتهاء الطلب"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

# ==========================================
# 5. تسجيل الموديلات (Model Registration)
# ==========================================
# يجب استدعاء جميع الموديلات هنا في أسفل الملف لتجنب مشكلة (Circular Imports).
# هذا يضمن أن Alembic سيرى دائماً جميع الجداول عبر Base.metadata
# يمكنك إضافة استدعاءات القطاعات المستقبلية هنا (مثل قطاع smart_bio أو logistics)
# مثال:
# from app.domains.identity.models import User
# from app.domains.academy.models import Course, Enrollment
# ... الخ