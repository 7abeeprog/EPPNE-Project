import asyncio
import sys
import os
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config
from alembic import context

# ==========================================
# 1. تعريف المسار الجذري للمشروع
# ==========================================
# لضمان نجاح عملية الاستيراد (Import) من مجلد app
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ==========================================
# 2. استيراد الإعدادات والقاعدة الأساسية السيادية
# ==========================================
from app.core.config import settings
from app.core.database import Base

# ==========================================
# 3. استيراد جميع النماذج (Models) وفق شجرة المشروع
# ==========================================
# تم سرد كافة القطاعات الـ 33 المكتشفة في البنية التحتية.
# إذا واجهت خطأ (ImportError) في أحدها لكونه فارغاً تماماً أو به خطأ، 
# قم بوضع علامة # أمامه مؤقتاً لتمرير عملية الهجرة.

from app.domains.academy.models import *
from app.domains.affiliate.models import *
from app.domains.agritech.models import *
from app.domains.ai_agents.models import *
from app.domains.ai_governance.models import *
from app.domains.arbitration_syndicates.models import *
from app.domains.automation.models import *
from app.domains.command.models import *
from app.domains.commerce.models import *
from app.domains.communications.models import *
from app.domains.digital_twin.models import *
from app.domains.employment.models import *
from app.domains.finance.models import *
from app.domains.health.models import *
from app.domains.identity.models import *
from app.domains.insurance.models import *
from app.domains.invitations.models import *
from app.domains.iot.models import *
from app.domains.logistics.models import *
from app.domains.manufacturing.models import *
from app.domains.privacy.models import *
from app.domains.projects.models import *
from app.domains.realestate.models import *
from app.domains.saas.models import *
from app.domains.service_marketplace.models import *
from app.domains.social.models import *
from app.domains.sovereign_entities.models import *
from app.domains.tenders_auctions.models import *
from app.domains.tourism_sports.models import *
from app.domains.translation.models import *
from app.domains.transport.models import *
from app.domains.zamakana.models import *

# ==========================================
# 4. إعدادات Alembic وتسجيل الأحداث
# ==========================================
config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# حقن الرابط الآمن لقاعدة البيانات من Pydantic Settings
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

# ربط محرك Alembic بالقاعدة الأساسية السيادية (Metadata)
target_metadata = Base.metadata

# ==========================================
# 5. دوال التنفيذ السيادية (متزامن ولا متزامن)
# ==========================================
def run_migrations_offline() -> None:
    """تشغيل الهجرة في وضع عدم الاتصال (Offline)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()

def do_run_migrations(connection) -> None:
    """تنفيذ الهجرة الفعلية داخل الاتصال."""
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()

async def run_async_migrations() -> None:
    """تشغيل الهجرة ببروتوكول لامتزامن (Async) ليتوافق تماماً مع محرك asyncpg."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()

def run_migrations_online() -> None:
    """تشغيل الهجرة في وضع الاتصال (Online)."""
    asyncio.run(run_async_migrations())

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()