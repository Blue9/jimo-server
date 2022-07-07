import uvicorn  # type: ignore

from app.utils import get_logger

log = get_logger(__name__)

if __name__ == "__main__":
    log.info("Running server")
    uvicorn.run("app.main:app", reload=True, host="0.0.0.0", port=80)
