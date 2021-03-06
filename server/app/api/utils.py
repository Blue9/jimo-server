import imghdr

from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.controllers import firebase, users
from app.models import models


def validate_user(user: models.User):
    if user is None or user.deleted:
        raise HTTPException(404, detail="User not found")


def check_can_view_user_else_raise(user: models.User, caller_uid: str = None,
                                   custom_exception: HTTPException = None):
    if user.uid == caller_uid:
        return
    if user.private_account:
        authorized = any(u.uid == caller_uid for u in user.followers)
        if not authorized:
            raise HTTPException(403, "Not authorized") if custom_exception is None else custom_exception


def get_uid_or_raise(authorization) -> str:
    uid = firebase.get_uid_from_auth_header(authorization)
    if uid is None:
        raise HTTPException(401, "Not authenticated")
    return uid


def get_user_or_raise(username: str, db: Session) -> models.User:
    user: models.User = users.get_user(db, username)
    validate_user(user)
    return user


def get_user_from_uid_or_raise(db: Session, uid: str) -> models.User:
    user: models.User = users.get_user_by_uid(db, uid)
    validate_user(user)
    return user


def check_valid_image(file: UploadFile):
    if file.content_type != "image/jpeg" or imghdr.what(file.file) != "jpeg":
        raise HTTPException(400, detail="File is not an image")
    file_size = 0
    for chunk in file.file:
        file_size += len(chunk)
        if file_size > 2 * 1024 * 1024:
            raise HTTPException(400, detail="Max file size is 2MB")
    file.file.seek(0)
