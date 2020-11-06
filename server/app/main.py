from fastapi import FastAPI

from app.routers import users, posts

app = FastAPI()


@app.get("/")
def index():
    return {"success": True}


app.include_router(users.router, prefix="/users")
app.include_router(posts.router, prefix="/posts")
