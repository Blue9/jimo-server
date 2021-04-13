import imghdr
from typing import Optional

from fastapi import HTTPException, UploadFile
from sqlalchemy import false
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.controllers import users
from app.controllers.firebase import FirebaseUser, FirebaseAdminProtocol
from app.models import models


def validate_user(db: Session, caller_user: models.User, user: Optional[models.User]):
    if user is None or user.deleted or users.is_blocked(db, blocked_by_user=user, blocked_user=caller_user):
        raise HTTPException(404, detail="User not found")


def validate_firebase_user(firebase_user: FirebaseUser, db: Session):
    is_valid_user = db.query(models.User.id) \
                        .filter(models.User.uid == firebase_user.uid, models.User.deleted == false()) \
                        .count() > 0
    if not is_valid_user:
        raise HTTPException(403, detail="Not authorized")


def get_user_from_uid_or_raise(db: Session, uid: str, lock=False) -> models.User:
    user: Optional[models.User] = users.get_user_by_uid(db, uid, lock=lock)
    if user is None or user.deleted:
        raise HTTPException(403)
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


def upload_image(file: UploadFile, user: models.User, firebase_admin: FirebaseAdminProtocol, db: Session,
                 override_used=False) -> models.ImageUpload:
    check_valid_image(file)
    # Set override_used to True if you plan to immediately use the image in a profile picture or post (as opposed to
    # returning the image ID to the user).
    image_upload: models.ImageUpload = models.ImageUpload(user_id=user.id, used=override_used)
    try:
        db.add(image_upload)
        db.commit()
    except IntegrityError:
        # Right now this only happens in the case of a UUID collision which should be almost impossible
        raise HTTPException(400, detail="Could not upload image")
    response = firebase_admin.upload_image(user, image_id=image_upload.external_id, file_obj=file.file)
    if response is None:
        db.delete(image_upload)
        db.commit()
        raise HTTPException(500, detail="Failed to upload image")
    blob_name, url = response
    image_upload.firebase_blob_name = blob_name
    image_upload.firebase_public_url = url
    db.commit()
    return image_upload
