import uuid
from contextlib import contextmanager
from typing import Optional
from unittest import mock

import pytest
from fastapi import HTTPException, Header
from fastapi.testclient import TestClient

from app import api
from app.api.admin import get_admin_or_raise
from app.controllers.firebase import FirebaseUser, get_firebase_user
from app.db.database import engine, get_session
from app.main import app as main_app
from app.models import models
from tests.mock_firebase import MockFirebaseAdmin
from tests.utils import init_db, reset_db

client = TestClient(main_app)
admin_header = {"Authorization": "Bearer admin_uid"}

INITIAL_POST_ID = uuid.uuid4()


@contextmanager
def request_as_admin(uid: str = "admin_uid"):
    with get_session() as session:
        user = session.query(models.User).filter(models.User.uid == uid).first()
    mock_get_admin = mock.Mock(return_value=user)
    main_app.dependency_overrides[get_firebase_user] = lambda: FirebaseUser(shared_firebase=MockFirebaseAdmin(),
                                                                            uid=uid)
    main_app.dependency_overrides[get_admin_or_raise] = lambda: mock_get_admin()
    yield
    main_app.dependency_overrides = {}
    mock_get_admin.assert_called_once()


def setup_module():
    init_db(engine)
    with get_session() as session:
        regular_user = models.User(uid="uid", username="user", first_name="first", last_name="last",
                                   phone_number="+18005551234")
        admin_user = models.User(uid="admin_uid", username="admin", first_name="first", last_name="last",
                                 phone_number="+18005551230", is_admin=True)
        deleted_admin = models.User(uid="deleted_uid", username="deleted_user", first_name="first", last_name="last",
                                    phone_number="+18005551235", deleted=True, is_admin=True)
        session.add(regular_user)
        session.add(admin_user)
        session.add(deleted_admin)
        session.commit()

        place = models.Place(name="test place", latitude=0, longitude=0)
        session.add(place)
        session.commit()

        new_post = models.Post(external_id=INITIAL_POST_ID, user_id=regular_user.id, place_id=place.id, category_id=1,
                               content="test")
        session.add(new_post)
        session.commit()


def teardown_module():
    reset_db(engine)


def test_get_admin_or_raise():
    with get_session() as session:
        with pytest.raises(HTTPException) as regular_user_exception:
            api.admin.get_admin_or_raise(FirebaseUser(shared_firebase=MockFirebaseAdmin(), uid="uid"), session)
        assert regular_user_exception.value.status_code == 403

        with pytest.raises(HTTPException) as deleted_admin_exception:
            api.admin.get_admin_or_raise(FirebaseUser(shared_firebase=MockFirebaseAdmin(), uid="deleted_uid"), session)
        assert deleted_admin_exception.value.status_code == 403

        admin = api.admin.get_admin_or_raise(FirebaseUser(shared_firebase=MockFirebaseAdmin(), uid="admin_uid"),
                                             session)
        assert admin is not None
        assert admin.is_admin


def test_auth_for_all_get_endpoints():
    all_routes = main_app.routes
    admin_routes = [route for route in all_routes if route.path.startswith("/admin") and "GET" in route.methods]
    url_param_map = {
        "{username}": "user",
        "{post_id}": str(INITIAL_POST_ID)
    }
    for route in admin_routes:
        route_deps = list(map(lambda dep: dep.call, route.dependant.dependencies))
        assert get_admin_or_raise in route_deps
        with request_as_admin():
            path = route.path
            for param, value in url_param_map.items():
                path = path.replace(param, value)
            response = client.get(path)
            assert response.status_code == 200


def test_create_update_users():
    path = "/admin/users"
    create_user_request = {
        "uid": "create_user_uid",
        "username": "user",  # Duplicate username, should fail
        "firstName": "First",
        "lastName": "Last",
    }
    with request_as_admin():
        create_user_response = client.post(path, json=create_user_request)
        assert create_user_response.status_code == 400

    create_user_request["username"] = "new_user"
    with request_as_admin():
        create_user_response = client.post(path, json=create_user_request)
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
    with request_as_admin():
        update_user_response = client.post(path, json=update_user_request)
        assert update_user_response.status_code == 400

    update_user_request["username"] = "new_user"
    with request_as_admin():
        update_user_response = client.post(path, json=update_user_request)
        assert update_user_response.status_code == 200


def test_create_update_post():
    with request_as_admin():
        all_posts = client.get("/admin/posts")
        assert all_posts.status_code == 200
        all_posts_json = all_posts.json()["data"]
        assert len(all_posts_json) == 1

    first_post = all_posts_json[0]
    path = f"/admin/posts/{first_post['postId']}"

    with request_as_admin():
        update_post_request = {"deleted": True}
        admin_user_response = client.post(path, json=update_post_request)
        assert admin_user_response.status_code == 200

    with request_as_admin():
        all_posts = client.get("/admin/posts")
        assert all_posts.status_code == 200
        all_posts_json = all_posts.json()["data"]
        assert len(all_posts_json) == 1
        assert all_posts_json[0]["deleted"]


def test_add_remove_invites():
    path = "/admin/invites"
    with request_as_admin():
        admin_user_response = client.post(path, json={"phoneNumber": "+18005554444"})
        assert admin_user_response.status_code == 200

    with request_as_admin():
        invites = client.get(path)
        assert invites.status_code == 200

        invites_json = invites.json()["data"]
        assert len(invites_json) == 1
        assert invites_json[0]["phoneNumber"] == "+18005554444"

    with request_as_admin():
        admin_user_response = client.delete(path, json={"phoneNumbers": ["+18005554444"]})
        assert admin_user_response.status_code == 200

    with request_as_admin():
        invites = client.get(path)
        assert invites.status_code == 200
        assert len(invites.json()["data"]) == 0
