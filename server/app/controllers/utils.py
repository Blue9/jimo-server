from psycopg2.errorcodes import UNIQUE_VIOLATION
from sqlalchemy.exc import IntegrityError


def is_unique_constraint_error(e: IntegrityError, constraint_name: str) -> bool:
    """Return whether the error a unique constraint violation for the given constraint name."""
    # Unfortunately there isn't a cleaner way than parsing the error message
    constraint_msg = f'unique constraint "{constraint_name}"'
    return e.orig.pgcode == UNIQUE_VIOLATION and constraint_msg in str(e)


def is_unique_column_error(e: IntegrityError, column_name: str) -> bool:
    """Return whether the error a unique constraint violation for the given column name."""
    return e.orig.pgcode == UNIQUE_VIOLATION and f"Key ({column_name})" in str(e)
