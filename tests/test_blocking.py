import uuid
from contextlib import contextmanager

import pytest
import pytest_asyncio

from app.core.database.models import UserRow, PlaceRow, PostRow
from app.core.firebase import get_firebase_user, FirebaseUser
from app.main import app as main_app
from tests.mock_firebase import MockFirebaseAdmin

pytestmark = pytest.mark.asyncio
USER_A_POST_ID = uuid.uuid4()
USER_B_POST_ID = uuid.uuid4()


@pytest_asyncio.fixture(autouse=True)
async def setup_fixture(session):
    user_a = UserRow(uid="a", username="a", first_name="a", last_name="a")
    user_b = UserRow(uid="b", username="b", first_name="b", last_name="b")
    session.add(user_a)
    session.add(user_b)
    await session.commit()

    place = PlaceRow(name="place_one", latitude=0, longitude=0)
    session.add(place)
    await session.commit()
    await session.refresh(user_a)
    await session.refresh(user_b)
    await session.refresh(place)

    user_a_post = PostRow(
        id=USER_A_POST_ID,
        user_id=user_a.id,
        place_id=place.id,
        category="food",
        content="",
    )
    user_b_post = PostRow(
        id=USER_B_POST_ID,
        user_id=user_b.id,
        place_id=place.id,
        category="food",
        content="",
    )
    session.add(user_a_post)
    session.add(user_b_post)
    await session.commit()


@contextmanager
def request_as(uid: str):
    main_app.dependency_overrides[get_firebase_user] = lambda: FirebaseUser(MockFirebaseAdmin(), uid=uid)
    yield
    main_app.dependency_overrides = {}


async def test_basic_blocking(client):
    block = lambda username: f"/users/{username}/block"  # noqa(E731)

    # Blocking other user is fine
    with request_as(uid="a"):
        response = await client.post(block("b"))
        assert response.status_code == 200
        assert response.json()["success"]

    # Blocking someone who has blocked you doesn't work
    with request_as(uid="b"):
        response = await client.post(block("a"))
        assert response.status_code == 404

    # Blocking yourself doesn't work
    with request_as(uid="b"):
        response = await client.post(block("b"))
        assert response.status_code == 400

    # Can't view someone who blocked you
    with request_as(uid="b"):
        response = await client.get("/users/a")
        assert response.status_code == 404
        response = await client.get("/users/a/posts")
        assert response.status_code == 404

    # Unblocking works fine
    with request_as(uid="a"):
        response = await client.post("/users/b/unblock")
        assert response.status_code == 200
