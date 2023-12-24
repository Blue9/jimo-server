import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import Connection
from sqlalchemy.orm import sessionmaker

from app.core import config
from app.core.database.models import Base
from app.features.posts import categories

TEST_DATABASE_NAME = "jimo_test_db"


@pytest_asyncio.fixture
async def engine():
    check_db_name()
    from app.core.database.engine import engine

    yield engine
    await engine.dispose()


@pytest.fixture(scope="session")
def app():
    from app.main import app as main_app

    return main_app


@pytest_asyncio.fixture
async def create(engine):
    async with engine.begin() as conn:
        await conn.run_sync(reset_db)
        await conn.run_sync(Base.metadata.create_all)
        await conn.run_sync(populate_categories)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(reset_db)


@pytest_asyncio.fixture
async def session(engine, create):
    async with AsyncSession(engine) as session:
        yield session


@pytest_asyncio.fixture
async def client(app):
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


def check_db_name():
    url = make_url(config.SQLALCHEMY_DATABASE_URL)
    db_name = url.database
    if db_name != TEST_DATABASE_NAME:
        pytest.exit(f"Database name must be {TEST_DATABASE_NAME}", returncode=1)


def populate_categories(connection):
    with sessionmaker(autocommit=False, autoflush=False, bind=connection)() as session:
        categories.add_categories_to_db(session)


def reset_db(connection: Connection):
    connection.execute(text("DROP SCHEMA public CASCADE"))
    connection.execute(text("CREATE SCHEMA public"))
    connection.execute(text("CREATE EXTENSION postgis"))
