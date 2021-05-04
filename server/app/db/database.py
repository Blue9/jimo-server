from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from starlette.requests import Request

from app.config import SQLALCHEMY_DATABASE_URL

# Some information about pool sizing: https://github.com/brettwooldridge/HikariCP/wiki/About-Pool-Sizing
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    pool_size=6,
    max_overflow=0,
    pool_timeout=15,  # seconds
    pool_recycle=1800,
    echo=False
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db(request: Request):
    request.state.db = SessionLocal()
    return request.state.db
    # The db session will be closed by the db_session_middleware in app.main
    # This is so that we close the session BEFORE the response is delivered,


@contextmanager
def get_session():
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()


Base = declarative_base()
