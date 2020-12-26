from typing import Optional, List

from fastapi import FastAPI, HTTPException, Header, Depends
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from sqlalchemy.orm import Session
from starlette.requests import Request
from starlette.responses import JSONResponse

from app import routers
from app.controllers import auth, users, places
from app.database import get_db
from app.models import schemas
from app.models.schemas import PrivateUser, Location

app = FastAPI()


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_request: Request, exc: RequestValidationError):
    errors = dict()
    for error in exc.errors():
        if "loc" not in error or "msg" not in error:
            continue
        errors[error["loc"][-1]] = error["msg"]
    return JSONResponse(status_code=400, content=jsonable_encoder({"errors": errors}))


@app.get("/")
def index():
    return {"success": True}


@app.get("/testToken/{email}")
def get_test_token(email: str):
    try:
        from starlette.responses import Response
        return Response(content=auth.get_test_token(email))
    except Exception:
        raise HTTPException(404)


@app.get("/me", response_model=PrivateUser)
def get_me(authorization: Optional[str] = Header(None), db: Session = Depends(get_db)):
    """Get the given user based on the auth details.

    Args:
        authorization: Authorization header. This string is automatically injected by FastAPI.
        db: The database session object. This object is automatically injected by FastAPI.

    Returns:
        The user.

    Raises:
        HTTPException: If the user could not be found (404) or the caller isn't authenticated (401).
    """
    email = auth.get_email_from_auth_header(authorization)
    if email is None:
        raise HTTPException(401, "Not authenticated")
    user = users.get_user_by_email(db, email)
    if user is None:
        raise HTTPException(404, "User not found")
    return user


@app.get("/place", response_model=List[schemas.Place])
def get_place(lat: float, long: float, db: Session = Depends(get_db)):
    from app.models.request_schemas import MaybeCreatePlaceRequest
    return places.get_place_or_create(db, MaybeCreatePlaceRequest(name="test",
                                                                  location=Location(latitude=lat, longitude=long)))


app.include_router(routers.users.router, prefix="/users")
app.include_router(routers.posts.router, prefix="/posts")
app.include_router(routers.search.router, prefix="/search")
