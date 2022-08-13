import os
from typing import Optional

SQLALCHEMY_DATABASE_URL: str = os.environ["DATABASE_URL"]

REDIS_URL: str = os.environ["REDIS_URL"]

RATE_LIMIT_CONFIG: Optional[str] = os.environ.get("RATE_LIMIT_CONFIG")

# Allow requests from this origin
ALLOW_ORIGIN: Optional[str] = os.environ.get("ALLOW_ORIGIN")

# If true, enable docs and openapi.json endpoints
ENABLE_DOCS: bool = os.environ.get("ENABLE_DOCS") == "1"

# Firebase storage bucket for user images
STORAGE_BUCKET: str = os.environ.get("STORAGE_BUCKET", "goodplaces-app.appspot.com")

# App-related configuration
_invites_per_user: Optional[str] = os.environ.get("INVITES_PER_USER")

INVITES_PER_USER: int = 100
if _invites_per_user:
    try:
        INVITES_PER_USER = int(_invites_per_user)
    except ValueError:
        print(f"Could not convert INVITES_PER_USER to int, defaulting to {INVITES_PER_USER}")
