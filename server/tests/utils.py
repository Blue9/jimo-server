from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker

from app.controllers import categories
from app.models import models


def reset_db(db_engine: Engine):
    with db_engine.connect() as connection:
        connection.execute("""DROP SCHEMA public CASCADE""")
        connection.execute("""CREATE SCHEMA public""")
        connection.execute("""CREATE EXTENSION postgis""")


def init_db(db_engine):
    with db_engine.connect() as connection:
        connection.execute("""CREATE EXTENSION IF NOT EXISTS postgis""")
    models.Base.metadata.create_all(bind=db_engine)
    Session = sessionmaker(bind=db_engine)
    session = Session()
    categories.add_categories_to_db(session)
    session.close()
