import uuid
from contextlib import contextmanager

import pytest
import pytest_asyncio

from app.core.database.models import UserRow, PlaceRow, PostRow
from app.core.firebase import get_firebase_user, FirebaseUser
from app.features.map.types import GetMapRequest, GetMapResponse
from app.features.places.entities import RectangularRegion
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
        id=USER_A_POST_ID, user_id=user_a.id, place_id=place.id, category="food", content="cool", stars=1
    )
    user_b_post = PostRow(id=USER_B_POST_ID, user_id=user_b.id, place_id=place.id, category="food", content="", stars=2)
    session.add(user_a_post)
    session.add(user_b_post)
    await session.commit()


@contextmanager
def request_as(uid: str):
    main_app.dependency_overrides[get_firebase_user] = lambda: FirebaseUser(MockFirebaseAdmin(), uid=uid)
    yield
    main_app.dependency_overrides = {}


async def test_get_map(client):
    with request_as(uid="b"):
        request = GetMapRequest(
            region=RectangularRegion(x_min=-50, y_min=-50, x_max=50, y_max=50),
            map_type="community",
            categories=None,
            user_ids=None,
            min_stars=1,
        )
        response = await client.post("/map/load", json=request.model_dump())
        assert response.status_code == 200
        response_json = response.json()
        map_response = GetMapResponse.model_validate(response_json)
        pins = map_response.pins
        assert len(pins) == 1
        assert pins[0].place_id == PLACE_ID
