import os
from dotenv import load_dotenv

# 1. تحميل متغيرات البيئة أولاً وقبل استدعاء أي ملف من المشروع
load_dotenv()

import asyncio
from logging.config import fileConfig
from urllib.parse import urlparse, urlunparse, quote_plus

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import create_async_engine

from alembic import context

from app.core.database import Base
from app.core.config import settings

# ==========================================
# 🔥 تسجيل النماذج (Models Registration) بترتيب الاعتماديات الدقيق
# ==========================================

# المستوى 1: القطاعات السيادية الأساسية
from app.domains.identity.models import *
from app.domains.saas.models import *
from app.domains.sovereign_entities.models import *

# المستوى 2: المحركات الأساسية والحوكمة
from app.domains.finance.models import *
from app.domains.ai_agents.models import *
from app.domains.ai_governance.models import *
from app.domains.privacy.models import *
from app.domains.command.models import *
from app.domains.automation.models import *
from app.domains.communications.models import *
from app.domains.digital_twin.models import *
from app.domains.translation.models import *

# المستوى 3: القطاعات التشغيلية والخدمية
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

# المستوى 4: قطاعات التفاعل، المجتمع، والزمكان
from app.domains.social.models import *
from app.domains.affiliate.models import *
from app.domains.arbitration_syndicates.models import *
from app.domains.invitations.models import *
from app.domains.zamakana.models import *

# this is the Alembic Config object
config = context.config

# ==========================================
# 🔥 قراءة الرابط الخام من البيئة أو الإعدادات
# ==========================================
raw_url = os.getenv("DATABASE_URL") or str(settings.DATABASE_URL)

# --- ترميز كلمة المرور لتجنب الأحرف الخاصة في الاتصال الفعلي ---
parsed = urlparse(raw_url)
if parsed.password:
    encoded_password = quote_plus(parsed.password)
    netloc = f"{parsed.username}:{encoded_password}@{parsed.hostname}"
    if parsed.port:
        netloc += f":{parsed.port}"
    url = urlunparse((parsed.scheme, netloc, parsed.path, parsed.params, parsed.query, parsed.fragment))
else:
    url = raw_url

# 🔥 نضع الرابط الخام (بدون ترميز) في config لتجنب مشكلة interpolation مع علامة %
config.set_main_option("sqlalchemy.url", raw_url)

print(f"✅ [Alembic] Connecting to database at: {url}")  # الرابط المرمَّز المستخدم فعلياً
# -------------------------------------------------------------

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Metadata للنماذج
target_metadata = Base.metadata

# ==========================================
# 🔥 تجاهل الفهرس المكرر ix_cert_entity
# ==========================================
def include_object(object, name, type_, reflected, compare_to):
    if type_ == "index" and name == "ix_cert_entity":
        return False
    return True

# ==========================================
# وضع التشغيل غير المتصل (offline)
# ==========================================
def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    # نستخدم الرابط الخام هنا أيضاً (لا مشكلة لأنه لا يتم اتصال فعلي)
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
        include_object=include_object,
    )
    with context.begin_transaction():
        context.run_migrations()

# ==========================================
# تنفيذ الترحيلات على اتصال متزامن
# ==========================================
def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
        include_object=include_object,
    )
    with context.begin_transaction():
        context.run_migrations()

# ==========================================
# وضع التشغيل المتصل (online) – غير متزامن
# ==========================================
async def run_async_migrations() -> None:
    """Run migrations asynchronously using the correct encoded URL."""
    # نستخدم الرابط المرمَّز للاتصال الفعلي
    connectable = create_async_engine(url, poolclass=pool.NullPool)
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()

def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    asyncio.run(run_async_migrations())

# ==========================================
# نقطة الدخول الرئيسية
# ==========================================
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()