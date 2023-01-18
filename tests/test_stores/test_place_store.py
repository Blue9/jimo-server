import uuid

import pytest
import pytest_asyncio

from app.core.database.models import PlaceRow, PlaceSaveRow, UserRow
from app.features.places.place_store import PlaceStore

pytestmark = pytest.mark.asyncio
USER_A_ID = uuid.uuid4()
PLACE_ID = uuid.uuid4()


@pytest_asyncio.fixture(autouse=True, scope="function")
async def setup_fixture(session):
    user_a = UserRow(id=USER_A_ID, uid="a", username="a", first_name="a", last_name="a")
    place = PlaceRow(id=PLACE_ID, name="place_one", latitude=0, longitude=0)
    place_save = PlaceSaveRow(user_id=USER_A_ID, place_id=PLACE_ID)
    session.add(user_a)
    session.add(place)
    session.add(place_save)
    await session.commit()


@pytest.fixture(scope="function")
def place_store(session):
    return PlaceStore(db=session)


async def test_get_saved_places(place_store: PlaceStore):
    saved_places = await place_store.get_saved_places(user_id=USER_A_ID, cursor=None, limit=100)
    assert len(saved_places) == 1
    assert saved_places[0].id == PLACE_ID
