import pytest
from fastapi import HTTPException

from app.controllers.firebase import FirebaseUser, get_firebase_user
from app.main import app as main_app
from shared.models import models
from tests.mock_firebase import MockFirebaseAdmin

pytestmark = pytest.mark.asyncio


@pytest.fixture(autouse=True, scope="function")
async def setup_fixture(session):
    user = models.User(uid="uid", username="user", first_name="first", last_name="last",
                       phone_number="+18005551234")
    deleted_user = models.User(uid="deleted_uid", username="deleted_user", first_name="first", last_name="last",
                               phone_number="+18005551235", deleted=True)
    session.add(user)
    session.add(deleted_user)
    await session.commit()
    await session.refresh(user)
    user_prefs = models.UserPrefs(user_id=user.id, follow_notifications=True, post_liked_notifications=True)
    session.add(user_prefs)
    await session.commit()


async def test_me_not_authenticated(client):
    def mock_get_firebase_user():
        raise HTTPException(401)

    main_app.dependency_overrides[get_firebase_user] = mock_get_firebase_user
    response = await client.get("/me")
    assert response.status_code == 401


async def test_me_nonexistent_user(client):
    def mock_get_firebase_user():
        return FirebaseUser(shared_firebase=MockFirebaseAdmin(), uid="fake_uid")

    main_app.dependency_overrides[get_firebase_user] = mock_get_firebase_user
    response = await client.get("/me")
    assert response.status_code == 404


async def test_me_user_exists(client):
    def mock_get_firebase_user():
        return FirebaseUser(shared_firebase=MockFirebaseAdmin(), uid="uid")

    main_app.dependency_overrides[get_firebase_user] = mock_get_firebase_user
    response = await client.get("/me")
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


async def test_me_deleted_user(client):
    def mock_get_firebase_user():
        return FirebaseUser(shared_firebase=MockFirebaseAdmin(), uid="deleted_uid")

    main_app.dependency_overrides[get_firebase_user] = mock_get_firebase_user
    response = await client.get("/me")
    assert response.status_code == 404
