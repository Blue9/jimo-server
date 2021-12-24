import io
from typing import Optional

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from alembic import command
from alembic.config import Config

from app.config import SQLALCHEMY_DATABASE_URL
from app.controllers import categories
from shared.models import models

engine = create_engine(
    f"postgresql://{SQLALCHEMY_DATABASE_URL.split('://')[1]}",
    pool_size=6,
    max_overflow=0,
    pool_timeout=15,  # seconds
    pool_recycle=1800,
    echo=False
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def main():
    run_migrations()


def init_db():
    with engine.connect() as connection:
        connection.execute("""CREATE EXTENSION IF NOT EXISTS postgis""")
    models.Base.metadata.create_all(bind=engine)
    with SessionLocal() as session:
        categories.add_categories_to_db(session)


def run_migrations():
    print("Running db migrations")
    alembic_cfg = Config("alembic.ini")
    current_revision = get_current_revision()
    if current_revision is None:
        # If alembic_version table doesn't exist, init db and stamp it with the most recent revision
        print("Creating tables and stamping version")
        init_db()
        command.stamp(alembic_cfg, "head")
    else:
        print("Migrating")
        command.upgrade(alembic_cfg, "head")
    print("Ran db migrations")


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
