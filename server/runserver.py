import uvicorn

from app import config
from init_db import init_db

if __name__ == "__main__":
    if config.INIT_DB:
        init_db()
    uvicorn.run("app.main:app", reload=True, host="0.0.0.0", port=80)
