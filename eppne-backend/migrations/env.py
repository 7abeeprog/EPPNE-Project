import os
from dotenv import load_dotenv

# 1. تحميل متغيرات البيئة أولاً وقبل استدعاء أي ملف من المشروع
load_dotenv()

import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

from app.core.database import Base
from app.core.config import settings

# ==========================================
# 🔥 تسجيل النماذج (Models Registration) بترتيب الاعتماديات الدقيق
# ==========================================

# المستوى 1: القطاعات السيادية الأساسية (Core & Identity Dependencies)
from app.domains.identity.models import *
from app.domains.auth.models import *
from app.domains.saas.models import *
from app.domains.sovereign_entities.models import *

# المستوى 2: المحركات الأساسية والحوكمة (Engines, Finance & Governance)
from app.domains.finance.models import *
from app.domains.ai_agents.models import *
from app.domains.ai_governance.models import *
from app.domains.privacy.models import *
from app.domains.command.models import *
from app.domains.automation.models import *
from app.domains.communications.models import *
from app.domains.digital_twin.models import *
from app.domains.translation.models import *

# المستوى 3: القطاعات التشغيلية والخدمية (Operations & Ecosystem)
from app.domains.commerce.models import *
from app.domains.academy.models import *
from app.domains.health.models import *
from app.domains.logistics.models import *
from app.domains.manufacturing.models import *
from app.domains.projects.models import *
from app.domains.realestate.models import *
from app.domains.service_marketplace.models import *
from app.domains.tenders_auctions.models import *
from app.domains.tourism_sports.models import *
from app.domains.transport.models import *
from app.domains.iot.models import *
from app.domains.agritech.models import *
from app.domains.employment.models import *
from app.domains.insurance.models import *

# المستوى 4: قطاعات التفاعل، المجتمع، والزمكان (Social & Engagement)
from app.domains.social.models import *
from app.domains.affiliate.models import *
from app.domains.arbitration_syndicates.models import *
from app.domains.invitations.models import *
from app.domains.zamakana.models import *

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# --- إجبار النظام على قراءة الرابط الصحيح من الإعدادات بأمان ---
config.set_main_option("sqlalchemy.url", str(settings.DATABASE_URL))
# -------------------------------------------------------------

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
target_metadata = Base.metadata

# ==========================================
# 🔥 دالة تجاهل الفهارس المكررة (لتجنب أخطاء autogenerate)
# ==========================================
def include_object(object, name, type_, reflected, compare_to):
    """
    دالة لتحديد ما إذا كان سيتم تضمين كائن معين في عملية الهجرة.
    نستخدمها لتجاهل الفهرس المكرر ix_cert_entity الذي يظهر في كل مرة.
    """
    if type_ == "index" and name == "ix_cert_entity":
        return False
    return True

# ==========================================

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,             # 🔥 تتبع تغييرات أنواع البيانات (Type changes)
        compare_server_default=True,   # 🔥 تتبع تغييرات القيم الافتراضية (Default values)
        include_object=include_object, # ✅ تجاهل الفهرس المكرر
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection, 
        target_metadata=target_metadata,
        compare_type=True,             # 🔥 تتبع تغييرات أنواع البيانات
        compare_server_default=True,   # 🔥 تتبع تغييرات القيم الافتراضية
        include_object=include_object, # ✅ تجاهل الفهرس المكرر
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """In this scenario we need to create an Engine
    and associate a connection with the context.
    """
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()