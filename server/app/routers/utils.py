from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.controllers import auth, users
from app.models import models


def validate_user(user: models.User):
    if user is None or user.deactivated:
        raise HTTPException(404, detail="User not found")


def check_can_view_user_else_raise(user: models.User, caller_email: str = None,
                                   custom_exception: HTTPException = None):
    if user.email == caller_email:
        return
    if user.private_account:
        authorized = any(u.email == caller_email for u in user.followers)
        if not authorized:
            raise HTTPException(403, "Not authorized") if custom_exception is None else custom_exception


def get_email_or_raise(authorization) -> str:
    email = auth.get_email_from_auth_header(authorization)
    if email is None:
        raise HTTPException(401, "Not authenticated")
    return email


def get_user_or_raise(username: str, db: Session) -> models.User:
    user: models.User = users.get_user(db, username)
    validate_user(user)
    return user


def get_user_from_email_or_raise(db: Session, email: str) -> models.User:
    user: models.User = users.get_user_by_email(db, email)
    validate_user(user)
    return user


def get_user_from_auth_or_raise(db: Session, authorization: str) -> models.User:
    user_email = get_email_or_raise(authorization)
    return get_user_from_email_or_raise(db, user_email)
