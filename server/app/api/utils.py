import imghdr

from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.controllers import users
from app.controllers.firebase import FirebaseUser
from app.models import models


def validate_user(user: models.User):
    if user is None or user.deleted:
        raise HTTPException(404, detail="User not found")


def validate_firebase_user(firebase_user: FirebaseUser, db: Session):
    is_valid_user = db.query(models.User.id).filter(models.User.uid == firebase_user.uid).count() > 0
    if not is_valid_user:
        raise HTTPException(403, detail="Not authorized")


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
