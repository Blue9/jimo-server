from sqlalchemy.orm import Session

from app.models.models import Category


def add_categories_to_db(db: Session):
    db.add(Category(name="food"))
    db.add(Category(name="activity"))
    db.add(Category(name="attraction"))
    db.add(Category(name="lodging"))
    db.add(Category(name="shopping"))
    db.commit()


def get_category_or_raise(db: Session, category_name: str) -> Category:
    """Get the category object for the given category name."""
    category = db.query(Category).filter(Category.name == category_name).first()
    if category is None:
        raise ValueError("Invalid category")
    return category
