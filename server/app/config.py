import os

SQLALCHEMY_DATABASE_URL = os.environ["DATABASE_URL"]
FIREBASE_API_KEY = os.environ.get("FIREBASE_API_KEY", "")
