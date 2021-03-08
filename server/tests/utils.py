from app.models import models


def reset_db(db_engine):
    db_engine.execute("""DROP SCHEMA public CASCADE""")
    db_engine.execute("""CREATE SCHEMA public""")
    db_engine.execute("""CREATE EXTENSION postgis""")


def init_db(db_engine):
    models.Base.metadata.create_all(bind=db_engine)
