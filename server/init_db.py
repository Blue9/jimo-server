import io
from typing import Optional

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app import config
from app.controllers import categories, users
from app.db.database import engine, SessionLocal, get_session
from app.models import models

PRINT_SCHEMA = False


def print_schema():
    def dump(sql, *multiparams, **params):  # noqa
        if type(sql) == str:
            print(sql)
        else:
            print(sql.compile(dialect=engine.dialect))

    print_engine = create_engine("postgresql://", strategy="mock", executor=dump)
    models.Base.metadata.create_all(print_engine, checkfirst=False)


def init_db():
    print("Creating tables...")
    models.Base.metadata.create_all(bind=engine)
    print("Created all tables!")
    run_db_migrations()
    with get_session() as session:
        categories.add_categories_to_db(session)
        if config.ADMIN_USER is not None:
            user = config.ADMIN_USER
            created, error = users.create_user_ignore_invite_status(
                session, user.uid, user.username, user.first_name, user.last_name)
            if created:
                created.is_admin = True
                session.commit()
                print("Created admin user with uid", user.uid)


def run_db_migrations():
    print("Running db migrations")
    alembic_cfg = Config("alembic.ini")
    current_revision = get_current_revision()
    if current_revision is None:
        # If alembic_version table doesn't exist, stamp it with the most recent revision
        print("Stamping version")
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
    init_db()

    if PRINT_SCHEMA:
        print_schema()
    else:
        print("Re-run with PRINT_SCHEMA = True to print schema")
