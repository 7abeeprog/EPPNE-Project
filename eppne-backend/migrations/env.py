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
# 🔥 تسجيل النماذج (Models Registration)
# ==========================================
# استدعاء ملفات النماذج ضروري جداً لكي يتعرف عليها Alembic (Autogenerate)

# 1. استيراد القطاعات الأساسية التي تعتمد عليها القطاعات الأخرى (مثل المؤسسات)
# 👈 هذا السطر يحل مشكلة (NoReferencedTableError: table 'tenants')

# 2. استيراد باقي القطاعات
from app.domains.identity.models import *
from app.domains.finance.models import *
from app.domains.commerce.models import *
from app.domains.academy.models import *
from app.domains.affiliate.models import *
from app.domains.saas.models import * # إذا كان يحتوي على Tenant/Entities
# ملاحظة مهنية: إذا كان اسم المجلد الخاص بقطاع المؤسسات لديك مختلفاً (مثلاً tenant بدلاً من organization)، 
# يرجى تعديل السطر رقم 20 ليتطابق مع اسم المجلد الفعلي.

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

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,             # 🔥 تتبع تغييرات أنواع البيانات (Type changes)
        compare_server_default=True,   # 🔥 تتبع تغييرات القيم الافتراضية (Default values)
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection, 
        target_metadata=target_metadata,
        compare_type=True,             # 🔥 تتبع تغييرات أنواع البيانات
        compare_server_default=True,   # 🔥 تتبع تغييرات القيم الافتراضية
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