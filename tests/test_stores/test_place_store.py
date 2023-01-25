import uuid

import pytest
import pytest_asyncio

from app.core.database.models import PlaceRow, PlaceSaveRow, UserRow
from app.features.places.place_store import PlaceStore

pytestmark = pytest.mark.asyncio
USER_A_ID = uuid.uuid4()
PLACE_ID = uuid.uuid4()
PLACE_2_ID = uuid.uuid4()
POST_ID = uuid.uuid4()


@pytest_asyncio.fixture(autouse=True, scope="function")
async def setup_fixture(session):
    user_a = UserRow(id=USER_A_ID, uid="a", username="a", first_name="a", last_name="a")
    place = PlaceRow(id=PLACE_ID, name="place_one", latitude=0, longitude=0)
    place_2 = PlaceRow(id=PLACE_2_ID, name="place_two", latitude=1, longitude=1)
    place_save = PlaceSaveRow(user_id=USER_A_ID, place_id=PLACE_ID, note="Want to go here")
    session.add(user_a)
    session.add(place)
    session.add(place_2)
    session.add(place_save)
    await session.commit()


@pytest.fixture(scope="function")
def place_store(session):
    return PlaceStore(db=session)


async def test_get_saved_places(place_store: PlaceStore):
    saved_places = await place_store.get_saved_places(user_id=USER_A_ID, cursor=None, limit=100)
    assert len(saved_places) == 1
    assert saved_places[0].place.id == PLACE_ID
    assert saved_places[0].note == "Want to go here"


async def test_is_place_saved(place_store: PlaceStore):
    assert await place_store.is_place_saved(USER_A_ID, PLACE_ID)
    assert not await place_store.is_place_saved(USER_A_ID, PLACE_2_ID)
    await place_store.save_place(USER_A_ID, PLACE_2_ID, note="", category=None)
    assert await place_store.is_place_saved(USER_A_ID, PLACE_2_ID)
