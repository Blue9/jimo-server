import io
from typing import Optional

from alembic.config import Config
from shared.models.models import Base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from alembic import command
from app.core.config import SQLALCHEMY_DATABASE_URL
from app.features.posts import categories
from app.utils import get_logger

engine = create_engine(
    f"postgresql://{SQLALCHEMY_DATABASE_URL.split('://')[1]}",
    pool_size=6,
    max_overflow=0,
    pool_timeout=15,  # seconds
    pool_recycle=1800,
    echo=False,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
log = get_logger(__name__)


def main():
    run_migrations()


def init_db():
    with engine.connect() as connection:
        connection.execute("""CREATE EXTENSION IF NOT EXISTS postgis""")
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as session:
        categories.add_categories_to_db(session)


def run_migrations():
    log.info("Running db migrations")
    alembic_cfg = Config("alembic.ini")
    current_revision = get_current_revision()
    if current_revision is None:
        # If alembic_version table doesn't exist, init db and stamp it with the most recent revision
        log.info("Creating tables and stamping version")
        init_db()
        command.stamp(alembic_cfg, "head")
    else:
        log.info("Migrating")
        command.upgrade(alembic_cfg, "head")
    log.info("Ran db migrations")


def get_current_revision() -> Optional[str]:
    output_buffer = io.StringIO()
    alembic_cfg = Config("alembic.ini", stdout=output_buffer)
    command.current(alembic_cfg)
    output = output_buffer.getvalue()
    if output:
        return output
    else:
        # If current revision doesn't exist, output is an empty string, so we return None here
        return None


if __name__ == "__main__":
    main()
