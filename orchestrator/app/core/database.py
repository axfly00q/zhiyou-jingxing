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

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
