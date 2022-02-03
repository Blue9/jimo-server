import uuid
from contextlib import contextmanager

import pytest
from shared import schemas
from shared.models import models

from app.controllers.firebase import get_firebase_user, FirebaseUser
from app.main import app as main_app
from tests.mock_firebase import MockFirebaseAdmin

pytestmark = pytest.mark.asyncio
USER_A_ID = uuid.uuid4()
USER_B_ID = uuid.uuid4()
USER_A_POST_ID = uuid.uuid4()
USER_B_POST_ID = uuid.uuid4()


@pytest.fixture(autouse=True, scope="function")
async def setup_fixture(session):
    user_a = models.User(id=USER_A_ID, uid="a", username="a", first_name="a", last_name="a")
    user_b = models.User(id=USER_B_ID, uid="b", username="b", first_name="b", last_name="b")
    session.add(user_a)
    session.add(user_b)
    await session.commit()

    place = models.Place(name="place_one", latitude=0, longitude=0)
    session.add(place)
    await session.commit()

    await session.refresh(user_a)
    await session.refresh(user_b)
    await session.refresh(place)

    user_a_post = models.Post(
        id=USER_A_POST_ID,
        user_id=user_a.id,
        place_id=place.id,
        category="food",
        content=""
    )
    user_b_post = models.Post(
        id=USER_B_POST_ID,
        user_id=user_b.id,
        place_id=place.id,
        category="food",
        content=""
    )
    session.add(user_a_post)
    session.add(user_b_post)
    await session.commit()


@contextmanager
def request_as(uid: str):
    main_app.dependency_overrides[get_firebase_user] = lambda: FirebaseUser(MockFirebaseAdmin(), uid=uid)
    yield
    main_app.dependency_overrides = {}


async def test_get_map(session, client):
    with request_as(uid="b"):
        response = await client.get("/me/mapV2")
        assert response.status_code == 200
        response_json = response.json()
        map_response = schemas.map.MapResponse.parse_obj(response_json)
        posts = map_response.posts
        assert len(posts) == 1
        assert posts[0].id == USER_B_POST_ID
    session.add(models.UserRelation(from_user_id=USER_B_ID, to_user_id=USER_A_ID, relation="following"))
    await session.commit()
    with request_as(uid="b"):
        response = await client.get("/me/mapV2")
        assert response.status_code == 200
        response_json = response.json()
        map_response = schemas.map.MapResponse.parse_obj(response_json)
        posts = map_response.posts
        assert len(posts) == 2
