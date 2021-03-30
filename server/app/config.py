import base64
import json
import os

from typing import Optional

from app.schemas.admin import CreateUserRequest

# Database URL
SQLALCHEMY_DATABASE_URL: str = os.environ["DATABASE_URL"]

# Allow requests from this origin
ALLOW_ORIGIN: Optional[str] = os.environ.get("ALLOW_ORIGIN")

# If true, enable docs and openapi.json endpoints
ENABLE_DOCS: bool = os.environ.get("ENABLE_DOCS") == "1"

# If ADMIN_USER is set, then when initializing and migrating the db we create a new user with the given information.
# ADMIN_USER is a base64-encoded JSON string and should include keys "uid", "username", "firstName", and "lastName"
_admin_user: Optional[str] = os.environ.get("ADMIN_USER")

ADMIN_USER: Optional[CreateUserRequest] = None
if _admin_user:
    json_string = base64.b64decode(_admin_user)
    ADMIN_USER = CreateUserRequest.parse_obj(json.loads(json_string))

# App-related configuration
_invites_per_user: Optional[str] = os.environ.get("INVITES_PER_USER")

INVITES_PER_USER: Optional[int] = 5
if _invites_per_user:
    INVITES_PER_USER = int(_invites_per_user)
