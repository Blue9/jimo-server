from shared.stores.user_store import UserStore
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.utils import get_user_store
from fastapi import FastAPI, Depends, UploadFile, File
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app import api, config
from shared import schemas
from app.api import utils
from app.controllers.firebase import FirebaseUser, get_firebase_user
from app.db.database import get_db


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


@app.middleware("http")
async def db_session_middleware(request: Request, call_next):
    response = Response("Internal server error", status_code=500)
    request.state.db = None
    try:
        response = await call_next(request)
    except Exception as e:
        raise e
        # print(f"Exception when handling request {request.url}", e)
    finally:
        if request.state.db is not None:
            await request.state.db.close()
    return response


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
async def index():
    return {"success": True}


@app.post("/images", response_model=schemas.image.ImageUploadResponse)
async def upload_image(
    file: UploadFile = File(...),
    firebase_user: FirebaseUser = Depends(get_firebase_user),
    db: AsyncSession = Depends(get_db),
    user_store: UserStore = Depends(get_user_store)
):
    """Upload the given image to Firebase if allowed, returning the image id (used for posts + profile pictures)."""
    user: schemas.internal.InternalUser = await api.utils.get_user_from_uid_or_raise(user_store, firebase_user.uid)
    image_upload = await utils.upload_image(file, user, firebase_user.shared_firebase, db)
    return schemas.image.ImageUploadResponse(image_id=image_upload.id)


app.include_router(api.me.router, prefix="/me")
app.include_router(api.notifications.router, prefix="/notifications")
app.include_router(api.users.router, prefix="/users")
app.include_router(api.comments.router, prefix="/comments")
app.include_router(api.posts.router, prefix="/posts")
app.include_router(api.places.router, prefix="/places")
app.include_router(api.search.router, prefix="/search")
app.include_router(api.waitlist.router, prefix="/waitlist")
app.include_router(api.feedback.router, prefix="/feedback")
app.include_router(api.admin.router, prefix="/admin")