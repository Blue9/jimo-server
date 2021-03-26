from sqlalchemy.orm import sessionmaker

from app.controllers import categories
from app.models import models


def reset_db(db_engine):
    db_engine.execute("""DROP SCHEMA public CASCADE""")
    db_engine.execute("""CREATE SCHEMA public""")
    db_engine.execute("""CREATE EXTENSION postgis""")


def init_db(db_engine):
    models.Base.metadata.create_all(bind=db_engine)
    Session = sessionmaker(bind=db_engine)
    session = Session()
    categories.add_categories_to_db(session)
    session.close()
