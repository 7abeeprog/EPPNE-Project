import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

import pytest_asyncio

from app.core.database import AsyncSessionLocal, engine
from app.core.redis_client import redis_client


@pytest_asyncio.fixture
async def db():
    """جلسة DB حقيقية (AsyncSessionLocal) لاستخدامها في regression tests ضد
    قاعدة البيانات الحقيقية — صفر mock/stub.

    ملاحظة مهمة (Windows): pytest-asyncio بيفتح event loop جديد لكل test
    function، لكن engine الداتابيز وعميل Redis عالميين (singletons في
    app/core/database.py و app/core/redis_client.py) بيحتفظوا بـconnections
    من الـloop السابق. لو test تاني في نفس الملف (أو ملف تاني في نفس التشغيلة)
    استخدم نفس الـpool، بيكراش بـ'Event loop is closed' (ProactorEventLoop).
    التخلص من الـpool/الاتصال بعد كل test بيضمن connections جديدة مربوطة
    بالـloop الصحيح للـtest اللي بعدها."""
    async with AsyncSessionLocal() as session:
        yield session
        await session.rollback()
    await engine.dispose()
    await redis_client.close()
