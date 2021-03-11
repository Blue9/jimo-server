from sqlalchemy.orm import Session

from app.models import models


def add_categories_to_db(db: Session):
    if db.query(models.Category).count() > 0:
        print("Already populated categories table, skipping...")
        return
    db.add(models.Category(name="food"))
    db.add(models.Category(name="activity"))
    db.add(models.Category(name="attraction"))
    db.add(models.Category(name="lodging"))
    db.add(models.Category(name="shopping"))
    db.commit()


def get_category_or_raise(db: Session, category_name: str) -> models.Category:
    """Get the category object for the given category name."""
    category = db.query(models.Category).filter(models.Category.name == category_name).first()
    if category is None:
        raise ValueError("Invalid category")
    return category
