from contextlib import asynccontextmanager
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine, AsyncSession
from app.core.config import SQLALCHEMY_DATABASE_URL

# Some information about pool sizing: https://github.com/brettwooldridge/HikariCP/wiki/About-Pool-Sizing
engine = create_async_engine(
    SQLALCHEMY_DATABASE_URL,
    pool_size=16,
    max_overflow=0,
    pool_timeout=15,  # seconds
    pool_recycle=1800,
    pool_pre_ping=True,
    echo=False,
)
SessionLocal = async_sessionmaker(engine, autocommit=False, autoflush=False, class_=AsyncSession)  # type: ignore


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with get_db_context() as db:
        yield db


@asynccontextmanager
async def get_db_context():
    db: AsyncSession = SessionLocal()
    try:
        yield db
    finally:
        await db.close()
