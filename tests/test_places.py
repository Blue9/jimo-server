import uuid
from contextlib import contextmanager

import pytest
import pytest_asyncio

from app.core.database.models import UserRow, PlaceRow, PostRow
from app.core.firebase import get_firebase_user, FirebaseUser
from app.features.places.entities import Location, Place
from app.features.places.types import GetPlaceDetailsResponse
from app.main import app as main_app
from tests.mock_firebase import MockFirebaseAdmin

pytestmark = pytest.mark.asyncio
USER_A_ID = uuid.uuid4()
USER_B_ID = uuid.uuid4()
PLACE_ID = uuid.uuid4()
USER_A_POST_ID = uuid.uuid4()
USER_B_POST_ID = uuid.uuid4()


@pytest_asyncio.fixture(autouse=True, scope="function")
async def setup_fixture(session):
    user_a = UserRow(id=USER_A_ID, uid="a", username="a", first_name="a", last_name="a")
    user_b = UserRow(id=USER_B_ID, uid="b", username="b", first_name="b", last_name="b")
    session.add(user_a)
    session.add(user_b)
    await session.commit()

    place = PlaceRow(id=PLACE_ID, name="place_one", latitude=0, longitude=0)
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
        content="cool",
    )
    user_b_post = PostRow(
        id=USER_B_POST_ID,
        user_id=user_b.id,
        place_id=place.id,
        category="food",
        content="really really cool",
    )
    session.add(user_a_post)
    session.add(user_b_post)
    await session.commit()


@contextmanager
def request_as(uid: str):
    main_app.dependency_overrides[get_firebase_user] = lambda: FirebaseUser(MockFirebaseAdmin(), uid=uid)
    yield
    main_app.dependency_overrides = {}


async def test_find_place_success(client):
    with request_as(uid="b"):
        response = await client.get("/places/matching", params=dict(name="place_one", latitude=0, longitude=0))
        assert response.status_code == 200
        response_json = response.json()
        place: Place = Place.parse_obj(response_json["place"])
        assert place == Place(
            placeId=PLACE_ID, name="place_one", region_name=None, location=Location(latitude=0, longitude=0)
        )


async def test_get_place_details(client):
    with request_as(uid="b"):
        response = await client.get(f"/places/{PLACE_ID}/details")
        assert response.status_code == 200
        response_json = response.json()
        get_place_response: GetPlaceDetailsResponse = GetPlaceDetailsResponse.parse_obj(response_json)
        assert len(get_place_response.community_posts) == 1
        assert len(get_place_response.following_posts) == 1
        assert get_place_response.place.id == PLACE_ID
