from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from sqlalchemy.ext.asyncio import AsyncSession

from fastapi import FastAPI, Depends, UploadFile, File
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app import api, config
from shared import schemas
from app.api import utils
from app.controllers.dependencies import WrappedUser, get_caller_user, get_authorization_header
from app.controllers.firebase import FirebaseUser, get_firebase_user
from app.db.database import get_db
from app.utils import get_logger

log = get_logger(__name__)


def get_app() -> FastAPI:
    log.info("Initializing server")
    if config.ENABLE_DOCS:
        log.warning("Enabling docs")
        _app = FastAPI()
    else:
        _app = FastAPI(openapi_url=None)
    if config.ALLOW_ORIGIN:
        log.warning("Setting allow origin to %s", config.ALLOW_ORIGIN)
        origins = [config.ALLOW_ORIGIN]
        _app.add_middleware(
            CORSMiddleware,
            allow_origins=origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    log.warning("Rate limiting to %s", config.RATE_LIMIT_CONFIG)
    _app.state.limiter = Limiter(
        key_func=get_authorization_header,
        default_limits=[config.RATE_LIMIT_CONFIG],
        storage_uri=config.REDIS_URL
    )
    _app.add_middleware(SlowAPIMiddleware)
    return _app


app = get_app()


@app.middleware("http")
async def db_session_middleware(request: Request, call_next):
    response = Response("Internal server error", status_code=500)
    request.state.db = None
    try:
        response = await call_next(request)
    except Exception:  # noqa
        log.exception("Exception when handling request %s", request.url)
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
        key = error["loc"][-1]
        if key == "__root__":
            key = "root"
        errors[key] = error["msg"]
    log.info("Request validation error %s", errors)
    return JSONResponse(status_code=400, content=jsonable_encoder(errors))


@app.exception_handler(RateLimitExceeded)
def rate_limit_exceeded_handler(_request: Request, _exc: RateLimitExceeded) -> Response:
    return JSONResponse({"error": "You are going too fast"}, status_code=429)


@app.get("/")
async def index():
    return {"success": True}


@app.post("/images", response_model=schemas.image.ImageUploadResponse)
async def upload_image(
    file: UploadFile = File(...),
    firebase_user: FirebaseUser = Depends(get_firebase_user),
    db: AsyncSession = Depends(get_db),
    wrapped_user: WrappedUser = Depends(get_caller_user)
):
    """Upload the given image to Firebase if allowed, returning the image id (used for posts + profile pictures)."""
    user: schemas.internal.InternalUser = wrapped_user.user
    image_upload = await utils.upload_image(file, user, firebase_user.shared_firebase, db)
    return schemas.image.ImageUploadResponse(image_id=image_upload.id)


app.include_router(api.me.router, prefix="/me")
app.include_router(api.mapV3.router, prefix="/map")
app.include_router(api.notifications.router, prefix="/notifications")
app.include_router(api.users.router, prefix="/users")
app.include_router(api.comments.router, prefix="/comments")
app.include_router(api.posts.router, prefix="/posts")
app.include_router(api.places.router, prefix="/places")
app.include_router(api.search.router, prefix="/search")
app.include_router(api.waitlist.router, prefix="/waitlist")
app.include_router(api.feedback.router, prefix="/feedback")
app.include_router(api.admin.router, prefix="/admin")
