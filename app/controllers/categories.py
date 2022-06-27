from sqlalchemy import select, func

from shared.models import models
from sqlalchemy.orm import Session

from app.utils import get_logger

log = get_logger(__name__)


def add_categories_to_db(db: Session):
    exists_query = db.execute(select(func.count()).select_from(models.Category))
    if exists_query.scalar() > 0:  # type: ignore
        log.info("Already populated categories table, skipping...")
        return
    db.add(models.Category(name="food"))
    db.add(models.Category(name="activity"))
    db.add(models.Category(name="attraction"))
    db.add(models.Category(name="lodging"))
    db.add(models.Category(name="shopping"))
    db.add(models.Category(name="nightlife"))
    db.commit()
