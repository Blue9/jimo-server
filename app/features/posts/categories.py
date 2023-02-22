from app.core.database.models import CategoryRow
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.utils import get_logger

log = get_logger(__name__)


def add_categories_to_db(db: Session):
    exists_query = db.execute(select(func.count()).select_from(CategoryRow))
    if exists_query.scalar() > 0:  # type: ignore
        log.info("Already populated categories table, skipping...")
        return
    db.add(CategoryRow(name="food"))
    db.add(CategoryRow(name="cafe"))
    db.add(CategoryRow(name="activity"))
    db.add(CategoryRow(name="attraction"))
    db.add(CategoryRow(name="lodging"))
    db.add(CategoryRow(name="shopping"))
    db.add(CategoryRow(name="nightlife"))
    db.commit()
