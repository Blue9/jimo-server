import uuid
from contextlib import contextmanager

import pytest
from fastapi import FastAPI
from starlette.testclient import TestClient

from app import schemas
from app.controllers.firebase import get_firebase_user, FirebaseUser
from app.db.database import engine, get_session
from app.main import app as main_app
from app.models import models
from tests.mock_firebase import MockFirebaseAdmin
from tests.utils import init_db, reset_db

USER_A_ID = uuid.uuid4()
USER_B_ID = uuid.uuid4()


@pytest.fixture
def app() -> FastAPI:
    return main_app


def setup_module():
    init_db(engine)


def teardown_module():
    reset_db(engine)


def setup_function():
    with get_session() as session:
        user_a = models.User(id=USER_A_ID, uid="a", username="a", first_name="a", last_name="a")
        user_b = models.User(id=USER_B_ID, uid="b", username="b", first_name="b", last_name="b")
        session.add(user_a)
        session.add(user_b)
        session.commit()

        a_follows_b = models.UserRelation(from_user_id=USER_A_ID, to_user_id=USER_B_ID,
                                          relation=models.UserRelationType.following)
        session.add(a_follows_b)
        session.commit()


def teardown_function():
    with get_session() as session:
        session.query(models.User).delete()
        session.query(models.Waitlist).delete()
        session.query(models.Invite).delete()
        session.query(models.Place).delete()
        session.commit()


@contextmanager
def request_as(app: FastAPI, uid: str):
    app.dependency_overrides[get_firebase_user] = lambda: FirebaseUser(MockFirebaseAdmin(), uid=uid)
    yield
    app.dependency_overrides = {}


def test_get_followers_list_empty(app: FastAPI):
    client = TestClient(app)
    with request_as(app, uid="b"):
        response = client.get("/users/a/followers")
        assert response.status_code == 200
        parsed = schemas.user.FollowFeedResponse.parse_obj(response.json())
        assert len(parsed.users) == 0
        assert parsed.cursor is None


def test_get_followers_list_one_follower(app: FastAPI):
    client = TestClient(app)
    with request_as(app, uid="b"):
        response = client.get("/users/b/followers")
        assert response.status_code == 200
        parsed = schemas.user.FollowFeedResponse.parse_obj(response.json())
        assert len(parsed.users) == 1
        assert parsed.users[0].relation is None
        assert parsed.users[0].user.id == USER_A_ID
        assert parsed.cursor is None


def test_get_followers_list_blocked(app: FastAPI):
    client = TestClient(app)

    with get_session() as session:
        b_blocks_a = models.UserRelation(from_user_id=USER_B_ID, to_user_id=USER_A_ID,
                                         relation=models.UserRelationType.blocked)
        session.add(b_blocks_a)
        session.commit()

    with request_as(app, uid="a"):
        response = client.get("/users/b/followers")
        assert response.status_code == 404

    with request_as(app, uid="b"):
        response = client.get("/users/a/followers")
        assert response.status_code == 200


def test_get_following_list_empty(app: FastAPI):
    client = TestClient(app)
    with request_as(app, uid="a"):
        response = client.get("/users/b/following")
        assert response.status_code == 200
        parsed = schemas.user.FollowFeedResponse.parse_obj(response.json())
        assert len(parsed.users) == 0
        assert parsed.cursor is None


def test_get_following_list_one_follower(app: FastAPI):
    client = TestClient(app)
    with request_as(app, uid="a"):
        response = client.get("/users/a/following")
        assert response.status_code == 200
        parsed = schemas.user.FollowFeedResponse.parse_obj(response.json())
        assert len(parsed.users) == 1
        assert parsed.users[0].relation == schemas.user.UserRelation.following
        assert parsed.users[0].user.id == USER_B_ID
        assert parsed.cursor is None


def test_get_following_list_blocked(app: FastAPI):
    client = TestClient(app)

    with get_session() as session:
        b_blocks_a = models.UserRelation(from_user_id=USER_B_ID, to_user_id=USER_A_ID,
                                         relation=models.UserRelationType.blocked)
        session.add(b_blocks_a)
        session.commit()

    with request_as(app, uid="a"):
        response = client.get("/users/b/following")
        assert response.status_code == 404

    with request_as(app, uid="b"):
        response = client.get("/users/a/following")
        assert response.status_code == 200
