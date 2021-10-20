import pytest
from sqlalchemy.engine.url import make_url

from app import config
from app.db.database import engine
from tests.utils import reset_db, init_db

TEST_DATABASE_NAME = "jimo_test_db"


def pytest_sessionstart(session):
    # Sanity checks to make sure we're not overwriting an existing db
    check_db_name()
    table_names = engine.table_names()
    non_postgis_table_names = [table for table in table_names if table != "spatial_ref_sys"]
    if len(non_postgis_table_names) > 0:
        pytest.exit(f"Expected 0 tables, found {non_postgis_table_names}", returncode=1)
    else:
        reset_db(engine)
        init_db(engine)


def pytest_sessionfinish(session, exitstatus):
    reset_db(engine)


def check_db_name():
    url = make_url(config.SQLALCHEMY_DATABASE_URL)
    db_name = url.database
    if db_name != TEST_DATABASE_NAME:
        pytest.exit(f"Database name must be {TEST_DATABASE_NAME}", returncode=1)
