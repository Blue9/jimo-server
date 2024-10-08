import uuid

import pytest
import pytest_asyncio

from app.core.database.models import PlaceRow, PostRow, PostSaveRow, UserRow
from app.features.map.entities import MapPin, MapPinIcon
from app.features.map.map_store import MapStore
from app.features.places.entities import Location, RectangularRegion

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

    place = PlaceRow(id=PLACE_ID, name="place_one", latitude=0, longitude=0)
    session.add(place)
    await session.commit()

    await session.refresh(user_a)
    await session.refresh(user_b)
    await session.refresh(place)

    user_a_post = PostRow(
        id=USER_A_POST_ID, user_id=user_a.id, place_id=place.id, category="food", content="post with content"
    )
    user_b_post = PostRow(id=USER_B_POST_ID, user_id=user_b.id, place_id=place.id, category="food", content="")
    session.add(user_a_post)
    session.add(user_b_post)
    await session.commit()

    session.add(PostSaveRow(user_id=USER_A_ID, post_id=USER_B_POST_ID))
    await session.commit()


@pytest.fixture(scope="function")
def map_store(session):
    return MapStore(db=session)


async def test_get_community_map(map_store: MapStore):
    pins = await map_store.get_map(
        user_id=USER_A_ID,
        user_icon_url=None,
        region=RectangularRegion(x_min=-50, y_min=-50, x_max=50, y_max=50),
        user_filter="community",
        categories=None,
        user_ids=None,
    )
    assert len(pins) == 1
    assert pins[0] == MapPin(
        place_id=PLACE_ID,
        location=Location(latitude=0, longitude=0),
        icon=MapPinIcon(category="food", icon_url=None, num_posts=1),
    )
