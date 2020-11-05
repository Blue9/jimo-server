from sqlalchemy import create_engine

from app.database import engine
from app.models import models

PRINT_SCHEMA = False


def print_schema():
    def dump(sql, *multiparams, **params):  # noqa
        if type(sql) == str:
            print(sql)
        else:
            print(sql.compile(dialect=engine.dialect))

    engine = create_engine('postgresql://', strategy='mock', executor=dump)  # noqa
    models.Base.metadata.create_all(engine, checkfirst=False)


if __name__ == "__main__":
    print("Creating tables...")
    models.Base.metadata.create_all(bind=engine)
    print("Created all tables!")

    if PRINT_SCHEMA:
        print_schema()
    else:
        print("Re-run with PRINT_SCHEMA = True to print schema")
