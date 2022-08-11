from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from starlette.requests import Request

from app.core.config import SQLALCHEMY_DATABASE_URL

# Some information about pool sizing: https://github.com/brettwooldridge/HikariCP/wiki/About-Pool-Sizing
engine = create_async_engine(
    SQLALCHEMY_DATABASE_URL,
    pool_size=6,
    max_overflow=0,
    pool_timeout=15,  # seconds
    pool_recycle=1800,
    pool_pre_ping=True,
    echo=False,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, class_=AsyncSession)


async def get_db(request: Request) -> AsyncSession:
    request.state.db = SessionLocal()
    return request.state.db
    # The db session will be closed by the db_session_middleware in app.main
    # This is so that we close the session BEFORE the response is delivered,
