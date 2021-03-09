from fastapi import FastAPI, HTTPException, Depends, UploadFile, File
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from starlette.requests import Request
from starlette.responses import JSONResponse

from app import schemas, api
from app.controllers import users
from app.controllers.firebase import FirebaseUser, get_firebase_user, FirebaseAdminProtocol
from app.db.database import get_db
from app.models import models

app = FastAPI()


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_request: Request, exc: RequestValidationError):
    errors = dict()
    for error in exc.errors():
        if "loc" not in error or "msg" not in error:
            continue
        errors[error["loc"][-1]] = error["msg"]
    print(errors)
    return JSONResponse(status_code=400, content=jsonable_encoder(errors))


@app.get("/")
def index():
    return {"success": True}


@app.get("/me", response_model=schemas.user.PrivateUser)
def get_me(firebase_user: FirebaseUser = Depends(get_firebase_user), db: Session = Depends(get_db)):
    """Get the given user based on the auth details.

    Args:
        firebase_user: Firebase user from auth header.
        db: The database session object. This object is automatically injected by FastAPI.

    Returns:
        The user.

    Raises:
        HTTPException: If the user could not be found (404) or the caller isn't authenticated (401).
    """
    user = users.get_user_by_uid(db, firebase_user.uid)
    if user is None:
        raise HTTPException(404, "User not found")
    return user


def _upload_image(file: UploadFile, user: models.User, firebase_admin: FirebaseAdminProtocol,
                  db: Session, override_used=False) -> models.ImageUpload:
    api.utils.check_valid_image(file)
    # Set override_used to True if you plan to immediately use the image in a profile picture or post (as opposed to
    # returning the image ID to the user).
    image_upload: models.ImageUpload = models.ImageUpload(user_id=user.id, used=override_used)
    try:
        db.add(image_upload)
        db.commit()
    except IntegrityError:
        # Right now this only happens in the case of a UUID collision which should be almost impossible
        raise HTTPException(400, detail="Could not upload image")
    response = firebase_admin.upload_image(user, image_id=image_upload.urlsafe_id, file_obj=file.file)
    if response is None:
        db.delete(image_upload)
        db.commit()
        raise HTTPException(500, detail="Failed to upload image")
    blob_name, url = response
    image_upload.firebase_blob_name = blob_name
    image_upload.firebase_public_url = url
    db.commit()
    return image_upload


@app.post("/me/photo", response_model=schemas.user.PrivateUser)
def upload_profile_picture(file: UploadFile = File(...),
                           firebase_user: FirebaseUser = Depends(get_firebase_user),
                           db: Session = Depends(get_db)):
    """Set the current user's profile picture."""
    user: models.User = api.utils.get_user_from_uid_or_raise(db, firebase_user.uid)
    old_profile_picture = user.profile_picture
    image_upload = _upload_image(file, user, firebase_user.shared_firebase, db, override_used=True)
    user.profile_picture_id = image_upload.id
    db.commit()
    if old_profile_picture:
        firebase_user.shared_firebase.delete_image(old_profile_picture.firebase_blob_name)
    return user


@app.post("/images", response_model=schemas.image.ImageUploadResponse)
def upload_image(file: UploadFile = File(...),
                 firebase_user: FirebaseUser = Depends(get_firebase_user),
                 db: Session = Depends(get_db)):
    """Upload the given image to Firebase if allowed, returning the image id (used for posts + profile pictures)."""
    user: models.User = api.utils.get_user_from_uid_or_raise(db, firebase_user.uid)
    image_upload = _upload_image(file, user, firebase_user.shared_firebase, db)
    return schemas.image.ImageUploadResponse(image_id=image_upload.urlsafe_id)


app.include_router(api.notifications.router, prefix="/notifications")
app.include_router(api.users.router, prefix="/users")
app.include_router(api.posts.router, prefix="/posts")
app.include_router(api.places.router, prefix="/places")
app.include_router(api.search.router, prefix="/search")
app.include_router(api.waitlist.router, prefix="/waitlist")
app.include_router(api.feedback.router, prefix="/feedback")
