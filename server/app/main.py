from fastapi import FastAPI, Depends, UploadFile, File
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from sqlalchemy.orm import Session
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from app import schemas, api, config
from app.api import utils
from app.controllers.firebase import FirebaseUser, get_firebase_user
from app.db.database import get_db
from app.models import models


def get_app() -> FastAPI:
    if config.ENABLE_DOCS:
        _app = FastAPI()
    else:
        _app = FastAPI(openapi_url=None)
    if config.ALLOW_ORIGIN:
        origins = [config.ALLOW_ORIGIN]
        _app.add_middleware(
            CORSMiddleware,
            allow_origins=origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    return _app


app = get_app()


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


@app.post("/images", response_model=schemas.image.ImageUploadResponse)
def upload_image(file: UploadFile = File(...),
                 firebase_user: FirebaseUser = Depends(get_firebase_user),
                 db: Session = Depends(get_db)):
    """Upload the given image to Firebase if allowed, returning the image id (used for posts + profile pictures)."""
    user: models.User = api.utils.get_user_from_uid_or_raise(db, firebase_user.uid)
    image_upload = utils.upload_image(file, user, firebase_user.shared_firebase, db)
    return schemas.image.ImageUploadResponse(image_id=image_upload.external_id)


app.include_router(api.me.router, prefix="/me")
app.include_router(api.notifications.router, prefix="/notifications")
app.include_router(api.users.router, prefix="/users")
app.include_router(api.posts.router, prefix="/posts")
app.include_router(api.places.router, prefix="/places")
app.include_router(api.search.router, prefix="/search")
app.include_router(api.waitlist.router, prefix="/waitlist")
app.include_router(api.feedback.router, prefix="/feedback")
app.include_router(api.admin.router, prefix="/admin")
