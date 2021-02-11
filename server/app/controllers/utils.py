import uuid
from typing import Callable, TypeVar

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

T = TypeVar("T")


def get_urlsafe_id() -> str:
    """Get a random url-safe id."""
    return str(uuid.uuid4())


def add_with_urlsafe_id(db: Session, create_model: Callable[[str], T], max_tries: int = 3) -> T:
    """Try to get a unique url-safe id to build the given model and add it to the database."""
    tries = max_tries
    while tries > 0:
        tries -= 1

        urlsafe_id = get_urlsafe_id()
        model = create_model(urlsafe_id)

        db.add(model)
        try:
            db.commit()
            return model
        except IntegrityError as e:
            db.rollback()
            error_message = str(e)
            print(error_message)
            if "post_urlsafe_id_key" in error_message:
                print("URL safe id collision!", urlsafe_id)
            else:
                # The error was caused by something else
                raise e
    raise ValueError(f"Failed to add post after {max_tries} tries.")
