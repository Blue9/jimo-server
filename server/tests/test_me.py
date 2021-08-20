from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.controllers.firebase import FirebaseUser, get_firebase_user
from app.db.database import engine, get_session
from app.main import app
from models import models
from tests.mock_firebase import MockFirebaseAdmin
from tests.utils import init_db, reset_db

client = TestClient(app)


def setup_module():
    init_db(engine)
    with get_session() as session:
        user = models.User(uid="uid", username="user", first_name="first", last_name="last",
                           phone_number="+18005551234")
        deleted_user = models.User(uid="deleted_uid", username="deleted_user", first_name="first", last_name="last",
                                   phone_number="+18005551235", deleted=True)
        session.add(user)
        session.add(deleted_user)
        session.commit()
        user_prefs = models.UserPrefs(user_id=user.id, follow_notifications=True, post_liked_notifications=True)
        session.add(user_prefs)
        session.commit()


def teardown_module():
    reset_db(engine)


def test_me_not_authenticated():
    def mock_get_firebase_user():
        raise HTTPException(401)

    app.dependency_overrides[get_firebase_user] = mock_get_firebase_user
    response = client.get("/me")
    assert response.status_code == 401


def test_me_nonexistent_user():
    def mock_get_firebase_user():
        return FirebaseUser(shared_firebase=MockFirebaseAdmin(), uid="fake_uid")

    app.dependency_overrides[get_firebase_user] = mock_get_firebase_user
    response = client.get("/me")
    assert response.status_code == 404


def test_me_user_exists():
    def mock_get_firebase_user():
        return FirebaseUser(shared_firebase=MockFirebaseAdmin(), uid="uid")

    app.dependency_overrides[get_firebase_user] = mock_get_firebase_user
    response = client.get("/me")
    assert response.status_code == 200
    user = response.json()
    assert "userId" in user
    user.pop("userId")
    assert user == {
        "username": "user",
        "firstName": "first",
        "lastName": "last",
        "profilePictureUrl": None,
        "followerCount": 0,
        "followingCount": 0,
        "postCount": 0
    }


def test_me_deleted_user():
    def mock_get_firebase_user():
        return FirebaseUser(shared_firebase=MockFirebaseAdmin(), uid="deleted_uid")

    app.dependency_overrides[get_firebase_user] = mock_get_firebase_user
    response = client.get("/me")
    assert response.status_code == 404
