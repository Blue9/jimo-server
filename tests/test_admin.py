import uuid
from contextlib import asynccontextmanager
from unittest import mock

import pytest
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app import api
from app.api.admin import get_admin_or_raise
from app.controllers.firebase import FirebaseUser, get_firebase_user
from app.main import app as main_app
from shared.models import models
from shared.stores.user_store import UserStore
from tests.mock_firebase import MockFirebaseAdmin

pytestmark = pytest.mark.asyncio
admin_header = {"Authorization": "Bearer admin_uid"}

INITIAL_POST_ID = uuid.uuid4()


@asynccontextmanager
async def request_as_admin(session: AsyncSession, uid: str = "admin_uid"):
    result = await session.execute(select(models.User).where(models.User.uid == uid))
    user = result.scalars().first()
    mock_get_admin = mock.Mock(return_value=user)
    main_app.dependency_overrides[get_firebase_user] = lambda: FirebaseUser(shared_firebase=MockFirebaseAdmin(),
                                                                            uid=uid)
    main_app.dependency_overrides[get_admin_or_raise] = lambda: mock_get_admin()
    yield
    main_app.dependency_overrides = {}
    mock_get_admin.assert_called_once()


@pytest.fixture(autouse=True, scope="function")
async def setup_fixture(session):
    regular_user = models.User(uid="uid", username="user", first_name="first", last_name="last",
                               phone_number="+18005551234")
    admin_user = models.User(uid="admin_uid", username="admin", first_name="first", last_name="last",
                             phone_number="+18005551230", is_admin=True)
    deleted_admin = models.User(uid="deleted_uid", username="deleted_user", first_name="first", last_name="last",
                                phone_number="+18005551235", deleted=True, is_admin=True)
    session.add(regular_user)
    session.add(admin_user)
    session.add(deleted_admin)
    await session.commit()

    place = models.Place(name="test place", latitude=0, longitude=0)
    session.add(place)
    await session.commit()
    await session.refresh(regular_user)
    await session.refresh(place)

    new_post = models.Post(id=INITIAL_POST_ID, user_id=regular_user.id, place_id=place.id, category="food",
                           content="test")
    session.add(new_post)
    await session.commit()


async def test_get_admin_or_raise(session):
    user_store = UserStore(session)
    with pytest.raises(HTTPException) as regular_user_exception:
        await api.admin.get_admin_or_raise(FirebaseUser(shared_firebase=MockFirebaseAdmin(), uid="uid"), user_store)
    assert regular_user_exception.value.status_code == 403

    with pytest.raises(HTTPException) as deleted_admin_exception:
        await api.admin.get_admin_or_raise(
            FirebaseUser(shared_firebase=MockFirebaseAdmin(), uid="deleted_uid"), user_store)
    assert deleted_admin_exception.value.status_code == 403

    admin = await api.admin.get_admin_or_raise(FirebaseUser(shared_firebase=MockFirebaseAdmin(), uid="admin_uid"),
                                               user_store)
    assert admin is not None
    assert admin.is_admin


async def test_auth_for_all_get_endpoints(session, client):
    all_routes = main_app.routes
    admin_routes = [route for route in all_routes if route.path.startswith("/admin") and "GET" in route.methods]
    url_param_map = {
        "{username}": "user",
        "{post_id}": str(INITIAL_POST_ID)
    }
    for route in admin_routes:
        route_deps = list(map(lambda dep: dep.call, route.dependant.dependencies))
        assert get_admin_or_raise in route_deps
        async with request_as_admin(session):
            path = route.path
            for param, value in url_param_map.items():
                path = path.replace(param, value)
            response = await client.get(path)
            assert response.status_code == 200


async def test_create_update_users(session, client):
    path = "/admin/users"
    create_user_request = {
        "uid": "create_user_uid",
        "username": "user",  # Duplicate username, should fail
        "firstName": "First",
        "lastName": "Last",
    }
    async with request_as_admin(session):
        create_user_response = await client.post(path, json=create_user_request)
        assert create_user_response.status_code == 400

    create_user_request["username"] = "new_user"
    async with request_as_admin(session):
        create_user_response = await client.post(path, json=create_user_request)
        assert create_user_response.status_code == 200

    # Update user
    path = "/admin/users/new_user"
    update_user_request = {
        "username": "user",  # Duplicate username again
        "firstName": "First",
        "lastName": "Last",
        "isFeatured": False,
        "isAdmin": False,
        "deleted": False
    }
    async with request_as_admin(session):
        update_user_response = await client.post(path, json=update_user_request)
        assert update_user_response.status_code == 400

    update_user_request["username"] = "new_user"
    async with request_as_admin(session):
        update_user_response = await client.post(path, json=update_user_request)
        assert update_user_response.status_code == 200


async def test_create_update_post(session, client):
    async with request_as_admin(session):
        all_posts = await client.get("/admin/posts")
        assert all_posts.status_code == 200
        all_posts_json = all_posts.json()["data"]
        assert len(all_posts_json) == 1

    first_post = all_posts_json[0]
    path = f"/admin/posts/{first_post['postId']}"

    async with request_as_admin(session):
        update_post_request = {"deleted": True}
        admin_user_response = await client.post(path, json=update_post_request)
        assert admin_user_response.status_code == 200

    async with request_as_admin(session):
        all_posts = await client.get("/admin/posts")
        assert all_posts.status_code == 200
        all_posts_json = all_posts.json()["data"]
        assert len(all_posts_json) == 1
        assert all_posts_json[0]["deleted"]


async def test_add_remove_invites(session, client):
    path = "/admin/invites"
    async with request_as_admin(session):
        admin_user_response = await client.post(path, json={"phoneNumber": "+18005554444"})
        assert admin_user_response.status_code == 200

    async with request_as_admin(session):
        invites = await client.get(path)
        assert invites.status_code == 200

        invites_json = invites.json()["data"]
        assert len(invites_json) == 1
        assert invites_json[0]["phoneNumber"] == "+18005554444"

    async with request_as_admin(session):
        admin_user_response = await client.request("DELETE", path, json={"phoneNumbers": ["+18005554444"]})
        assert admin_user_response.status_code == 200

    async with request_as_admin(session):
        invites = await client.get(path)
        assert invites.status_code == 200
        assert len(invites.json()["data"]) == 0
