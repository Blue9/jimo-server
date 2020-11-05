from fastapi import FastAPI

from app.routers import users

app = FastAPI()


@app.get("/")
def index():
    return {"success": True}


app.include_router(users.router, prefix="/users")
