from sqlalchemy import select, func
from sqlalchemy.orm import Session

from models import models


def add_categories_to_db(db: Session):
    if db.execute(select(func.count()).select_from(models.Category)).scalar() > 0:
        print("Already populated categories table, skipping...")
        return
    db.add(models.Category(name="food"))
    db.add(models.Category(name="activity"))
    db.add(models.Category(name="attraction"))
    db.add(models.Category(name="lodging"))
    db.add(models.Category(name="shopping"))
    db.commit()
