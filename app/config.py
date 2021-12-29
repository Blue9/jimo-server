import os

from typing import Optional

# Database URL
from app.controllers.tasks import CloudTasksConfig

SQLALCHEMY_DATABASE_URL: str = os.environ["DATABASE_URL"]

REDIS_URL: str = os.environ["REDIS_URL"]

# Allow requests from this origin
ALLOW_ORIGIN: Optional[str] = os.environ.get("ALLOW_ORIGIN")

# If true, enable docs and openapi.json endpoints
ENABLE_DOCS: bool = os.environ.get("ENABLE_DOCS") == "1"

# Firebase storage bucket for user images
STORAGE_BUCKET: str = os.environ.get("STORAGE_BUCKET", "goodplaces-app.appspot.com")

# Cloud Tasks config
CLOUD_TASKS_CONFIG: Optional[CloudTasksConfig] = None
_cloud_tasks_config: Optional[str] = os.environ.get("CLOUD_TASKS_CONFIG")
if _cloud_tasks_config:
    try:
        CLOUD_TASKS_CONFIG = CloudTasksConfig.parse_raw(_cloud_tasks_config)
    except ValueError:
        print(f"Malformed cloud tasks config: {_cloud_tasks_config}")

# App-related configuration
_invites_per_user: Optional[str] = os.environ.get("INVITES_PER_USER")

INVITES_PER_USER: int = 100
if _invites_per_user:
    try:
        INVITES_PER_USER = int(_invites_per_user)
    except ValueError:
        print(f"Could not convert INVITES_PER_USER to int, defaulting to {INVITES_PER_USER}")
