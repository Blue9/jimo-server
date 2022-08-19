from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

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
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, class_=AsyncSession)


async def get_db():
    db: AsyncSession = SessionLocal()
    try:
        yield db
    finally:
        await db.close()
