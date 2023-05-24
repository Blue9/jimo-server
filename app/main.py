from fastapi import FastAPI, Depends, UploadFile, File
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.openapi.utils import get_openapi
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response, RedirectResponse
from timing_asgi import TimingMiddleware, TimingClient  # type: ignore
from timing_asgi.integrations import StarletteScopeToName  # type: ignore

from app.core import config
from app.core.database.engine import get_db
from app.core.database.models import LocationPingRow
from app.core.firebase import FirebaseUser, get_firebase_user
from app.core.types import SimpleResponse
from app.features.admin.routes import router as admin_router
from app.features.comments.routes import router as comment_router
from app.features.feedback.routes import router as feedback_router
from app.features.images import image_utils
from app.features.images.types import ImageUploadResponse
from app.features.map.routes import router as map_router
from app.features.me import router as me_router
from app.features.notifications.routes import router as notification_router
from app.features.places.routes import router as place_router
from app.features.places.types import PingLocationRequest
from app.features.posts.routes import router as post_router
from app.features.search.routes import router as search_router
from app.features.onboarding.routes import router as onboarding_router
from app.features.users.dependencies import get_authorization_header, get_caller_user
from app.features.users.entities import InternalUser
from app.features.users.routes import router as user_router
from app.utils import get_logger


log = get_logger(__name__)
log.info("Initializing server")
app = FastAPI(openapi_url="/openapi.json" if config.ENABLE_DOCS else None)
limiter = Limiter(key_func=get_authorization_header)
app.state.limiter = limiter
app.title = "Jimo"


class PrintTimings(TimingClient):
    def timing(self, metric_name, timing, tags):
        log.debug(dict(route=metric_name.removeprefix("main.app.features."), timing=timing, tags=tags))


app.add_middleware(TimingMiddleware, client=PrintTimings(), metric_namer=StarletteScopeToName("main", app))

if config.ENABLE_DOCS:
    log.warning("Docs enabled")
if config.ALLOW_ORIGIN:
    log.warning("Setting allow origin to %s", config.ALLOW_ORIGIN)
    origins = [config.ALLOW_ORIGIN]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


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
    return RedirectResponse("https://www.jimoapp.com/")


@app.post("/images", response_model=ImageUploadResponse)
async def upload_image(
    file: UploadFile = File(...),
    firebase_user: FirebaseUser = Depends(get_firebase_user),
    db: AsyncSession = Depends(get_db),
    user: InternalUser = Depends(get_caller_user),
):
    """Upload the given image to Firebase if allowed, returning the image id (used for posts + profile pictures)."""
    image_upload = await image_utils.upload_image(file, user, firebase_user.shared_firebase, db)
    return ImageUploadResponse(image_id=image_upload.id)


@app.post("/location/ping", response_model=SimpleResponse)
@limiter.limit("10/minute")
async def ping_location(
    request: Request,  # This needs to be here for limiter
    req: PingLocationRequest,
    firebase_user: FirebaseUser = Depends(get_firebase_user),
    db: AsyncSession = Depends(get_db),
):
    """TODO: Clean up and move."""
    ping = LocationPingRow(uid=firebase_user.uid, latitude=req.location.latitude, longitude=req.location.longitude)
    db.add(ping)
    try:
        await db.commit()
        return SimpleResponse(success=True)
    except Exception:
        await db.rollback()
        return SimpleResponse(success=True)


app.include_router(me_router, prefix="/me")
app.include_router(map_router, prefix="/map")
app.include_router(notification_router, prefix="/notifications")
app.include_router(user_router, prefix="/users")
app.include_router(comment_router, prefix="/comments")
app.include_router(post_router, prefix="/posts")
app.include_router(place_router, prefix="/places")
app.include_router(search_router, prefix="/search")
app.include_router(onboarding_router, prefix="/onboarding")
app.include_router(feedback_router, prefix="/feedback")
app.include_router(admin_router, prefix="/admin")
