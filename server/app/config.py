import os

SQLALCHEMY_DATABASE_URL = os.environ["DATABASE_URL"]

# App-related configuration
INVITES_PER_USER = os.environ.get("INVITES_PER_USER", 5)
