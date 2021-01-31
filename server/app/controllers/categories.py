from sqlalchemy.orm import Session

from app.models.models import Category


def add_categories_to_db(db: Session):
    db.add(Category(name="food"))
    db.add(Category(name="activity"))
    db.add(Category(name="attraction"))
    db.add(Category(name="lodging"))
    db.add(Category(name="shopping"))
    db.commit()
