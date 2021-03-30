from alembic import command
from alembic.config import Config

from app import config
from app.controllers import users
from app.db.database import get_session


def run_migrations():
    print("Running db migrations")
    alembic_cfg = Config("alembic.ini")
    command.upgrade(alembic_cfg, "head")
    print("Ran db migrations")
    with get_session() as session:
        if config.ADMIN_USER is not None:
            user = config.ADMIN_USER
            created, error = users.create_user_ignore_invite_status(
                session, user.uid, user.username, user.first_name, user.last_name)
            if created:
                created.is_admin = True
                session.commit()
                print("Created admin user with uid", user.uid)


if __name__ == "__main__":
    run_migrations()
