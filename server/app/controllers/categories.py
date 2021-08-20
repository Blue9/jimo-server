from sqlalchemy import select, func, exists
from sqlalchemy.orm import Session

from app.models import models


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


def get_category_or_raise(db: Session, category_name: str) -> str:
    """Get the category object for the given category name."""
    query = select(models.Category).where(models.Category.name == category_name)
    category = db.execute(exists(query).select()).scalar()
    if not category:
        raise ValueError("Invalid category")
    return category_name
