import uuid
from contextlib import contextmanager

import pytest
import pytest_asyncio
from shared.api.place import Region
from shared.models.models import UserRow, PlaceRow, PostRow

from app.core.firebase import get_firebase_user, FirebaseUser
from app.features.map.types import GetMapRequest, MapResponseV3
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


async def test_get_map(client):
    with request_as(uid="b"):
        request = GetMapRequest(region=Region(latitude=0, longitude=0, radius=10e6), categories=None)
        response = await client.post("/map/global", json=request.dict())
        assert response.status_code == 200
        response_json = response.json()
        map_response = MapResponseV3.parse_obj(response_json)
        pins = map_response.pins
        assert len(pins) == 1
        assert pins[0].place_id == PLACE_ID
