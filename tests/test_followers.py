import uuid
from contextlib import contextmanager

import pytest
import pytest_asyncio

from app.core.database.models import UserRow, UserRelationRow, UserRelationType
from app.core.firebase import get_firebase_user, FirebaseUser
from app.features.users.types import FollowFeedResponse
from app.main import app as main_app
from tests.mock_firebase import MockFirebaseAdmin

pytestmark = pytest.mark.asyncio
USER_A_ID = uuid.uuid4()
USER_B_ID = uuid.uuid4()


@pytest_asyncio.fixture(autouse=True)
async def setup_fixture(session):
    user_a = UserRow(id=USER_A_ID, uid="a", username="a", first_name="a", last_name="a")
    user_b = UserRow(id=USER_B_ID, uid="b", username="b", first_name="b", last_name="b")
    session.add(user_a)
    session.add(user_b)
    await session.commit()

    a_follows_b = UserRelationRow(
        from_user_id=USER_A_ID,
        to_user_id=USER_B_ID,
        relation=UserRelationType.following,
    )
    session.add(a_follows_b)
    await session.commit()


@contextmanager
def request_as(uid: str):
    main_app.dependency_overrides[get_firebase_user] = lambda: FirebaseUser(MockFirebaseAdmin(), uid=uid)
    yield
    main_app.dependency_overrides = {}


async def test_get_followers_list_empty(client):
    with request_as(uid="b"):
        response = await client.get("/users/a/followers")
        assert response.status_code == 200
        parsed = FollowFeedResponse.model_validate(response.json())
        assert len(parsed.users) == 0
        assert parsed.cursor is None


async def test_get_followers_list_one_follower(client):
    with request_as(uid="b"):
        response = await client.get("/users/b/followers")
        assert response.status_code == 200
        parsed = FollowFeedResponse.model_validate(response.json())
        assert len(parsed.users) == 1
        assert parsed.users[0].relation is None
        assert parsed.users[0].user.id == USER_A_ID
        assert parsed.cursor is None


async def test_get_followers_list_blocked(session, client):
    b_blocks_a = UserRelationRow(from_user_id=USER_B_ID, to_user_id=USER_A_ID, relation=UserRelationType.blocked)
    session.add(b_blocks_a)
    await session.commit()

    with request_as(uid="a"):
        response = await client.get("/users/b/followers")
        assert response.status_code == 404

    with request_as(uid="b"):
        response = await client.get("/users/a/followers")
        assert response.status_code == 200


async def test_get_following_list_empty(client):
    with request_as(uid="a"):
        response = await client.get("/users/b/following")
        assert response.status_code == 200
        parsed = FollowFeedResponse.model_validate(response.json())
        assert len(parsed.users) == 0
        assert parsed.cursor is None


async def test_get_following_list_one_follower(client):
    with request_as(uid="a"):
        response = await client.get("/users/a/following")
        assert response.status_code == 200
        parsed = FollowFeedResponse.model_validate(response.json())
        assert len(parsed.users) == 1
        assert parsed.users[0].relation == "following"
        assert parsed.users[0].user.id == USER_B_ID
        assert parsed.cursor is None


async def test_get_following_list_blocked(session, client):
    b_blocks_a = UserRelationRow(from_user_id=USER_B_ID, to_user_id=USER_A_ID, relation=UserRelationType.blocked)
    session.add(b_blocks_a)
    await session.commit()

    with request_as(uid="a"):
        response = await client.get("/users/b/following")
        assert response.status_code == 404

    with request_as(uid="b"):
        response = await client.get("/users/a/following")
        assert response.status_code == 200
