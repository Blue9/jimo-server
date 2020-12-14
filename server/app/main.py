from typing import Optional

from fastapi import FastAPI, HTTPException, Header, Depends
from sqlalchemy.orm import Session

from app.controllers import auth, controller
from app.database import get_db
from app.models.schemas import PrivateUser
from app.routers import users, posts

app = FastAPI()


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
    email = auth.get_email_from_token(authorization)
    if email is None:
        raise HTTPException(401, "Not authenticated")
    user = controller.get_user_by_email(db, email)
    if user is None:
        raise HTTPException(404, "User not found")
    return user


app.include_router(users.router, prefix="/users")
app.include_router(posts.router, prefix="/posts")
