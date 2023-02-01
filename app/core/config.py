import os
from typing import Optional

# Database connection URL (async)
# Example: "postgresql+asyncpg://user@localhost/jimo_db"
SQLALCHEMY_DATABASE_URL: str = os.environ["DATABASE_URL"]

# If specified, new posts will send a Slack message using the given webhook URL.
# Example: "https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXXXXXX"
SLACK_HOOK: Optional[str] = os.environ.get("SLACK_HOOK")

# Allow requests from this origin
ALLOW_ORIGIN: Optional[str] = os.environ.get("ALLOW_ORIGIN")

# If true, enable docs and openapi.json endpoints
ENABLE_DOCS: bool = os.environ.get("ENABLE_DOCS") == "1"

# Firebase storage bucket for user images
STORAGE_BUCKET: str = os.environ.get("STORAGE_BUCKET", "goodplaces-app.appspot.com")
