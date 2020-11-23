from fastapi import FastAPI, HTTPException

from app.controllers import auth
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


app.include_router(users.router, prefix="/users")
app.include_router(posts.router, prefix="/posts")
