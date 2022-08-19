import uuid

import pytest
import pytest_asyncio

from app.core.database.models import PlaceRow
from app.features.places.place_store import PlaceStore

pytestmark = pytest.mark.asyncio
USER_A_ID = uuid.uuid4()
USER_B_ID = uuid.uuid4()
PLACE_ID = uuid.uuid4()
USER_A_POST_ID = uuid.uuid4()
USER_B_POST_ID = uuid.uuid4()


@pytest_asyncio.fixture(autouse=True, scope="function")
async def setup_fixture(session):
    place = PlaceRow(id=PLACE_ID, name="place_one", latitude=0, longitude=0)
    session.add(place)
    await session.commit()


@pytest.fixture(scope="function")
def place_store(session):
    return PlaceStore(db=session)
