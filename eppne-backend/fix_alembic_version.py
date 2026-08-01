# fix_alembic_version.py
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

DATABASE_URL = "postgresql+asyncpg://eppne:eppne123@127.0.0.1:5435/eppne_v2"

async def fix():
    engine = create_async_engine(DATABASE_URL, echo=True)
    async with engine.connect() as conn:
        await conn.execute(text("ALTER TABLE alembic_version ALTER COLUMN version_num TYPE VARCHAR(64);"))
        await conn.commit()
        print("✅ Column `version_num` extended to VARCHAR(64)")
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(fix())