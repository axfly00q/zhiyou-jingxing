"""异步 SQLAlchemy 引擎与 Session 工厂。"""
from __future__ import annotations

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings


class Base(DeclarativeBase):
    pass


engine = create_async_engine(settings.database_url, future=True, echo=False, pool_pre_ping=True)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session


async def init_db() -> None:
    """开发环境快速建表；生产请用 Alembic 迁移。"""
    from app.models import all_models  # noqa: F401  确保模型被加载
    from sqlalchemy import text

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # 轻量迁移：为已存在的表追加新列（PG 支持 IF NOT EXISTS）
        for ddl in (
            "ALTER TABLE avatar ADD COLUMN IF NOT EXISTS model_type VARCHAR(16) DEFAULT 'vrm'",
            "ALTER TABLE avatar ADD COLUMN IF NOT EXISTS model_url VARCHAR(255)",
            "ALTER TABLE avatar ADD COLUMN IF NOT EXISTS default_motion VARCHAR(32) DEFAULT 'idle'",
        ):
            await conn.execute(text(ddl))
