import uuid

import pytest
import pytest_asyncio

from app.core.database.models import PlaceRow, PostRow, UserRow
from app.features.posts.post_store import PostStore

pytestmark = pytest.mark.asyncio
USER_A_ID = uuid.uuid4()
USER_B_ID = uuid.uuid4()
PLACE_ONE_ID = uuid.uuid4()
PLACE_TWO_ID = uuid.uuid4()
USER_A_POST_ID = uuid.uuid4()
USER_B_POST_ID = uuid.uuid4()


@pytest_asyncio.fixture(autouse=True, scope="function")
async def setup_fixture(session):
    user_a = UserRow(id=USER_A_ID, uid="a", username="a", first_name="a", last_name="a")
    user_b = UserRow(id=USER_B_ID, uid="b", username="b", first_name="b", last_name="b")
    session.add(user_a)
    session.add(user_b)

    place_one = PlaceRow(id=PLACE_ONE_ID, name="place_one", latitude=0, longitude=0)
    place_two = PlaceRow(id=PLACE_TWO_ID, name="place_two", latitude=10, longitude=10)
    session.add(place_one)
    session.add(place_two)
    await session.commit()

    await session.refresh(user_a)
    await session.refresh(user_b)
    await session.refresh(place_one)
    await session.refresh(place_two)

    user_a_post = PostRow(id=USER_A_POST_ID, user_id=user_a.id, place_id=place_one.id, category="food", content="")
    user_b_post = PostRow(id=USER_B_POST_ID, user_id=user_b.id, place_id=place_two.id, category="food", content="")
    session.add(user_a_post)
    session.add(user_b_post)
    await session.commit()


@pytest.fixture(scope="function")
def post_store(session):
    return PostStore(db=session)


async def test_get_post_by_id(post_store: PostStore):
    post = await post_store.get_post(USER_A_POST_ID)
    assert post is not None
    assert post.id == USER_A_POST_ID


async def test_is_post_liked(post_store: PostStore):
    is_liked = await post_store.is_post_liked(USER_A_POST_ID, USER_B_ID)
    assert not is_liked

    await post_store.like_post(USER_B_ID, USER_A_POST_ID)
    is_liked = await post_store.is_post_liked(USER_A_POST_ID, USER_B_ID)
    assert is_liked


async def test_update_post(post_store: PostStore):
    # Update using place_id
    updated_post = await post_store.update_post(
        USER_A_POST_ID, PLACE_TWO_ID, category="activity", content="new content", media_ids=[], stars=3
    )
    assert updated_post.place.id == PLACE_TWO_ID
    assert updated_post.content == "new content"
    assert updated_post.category == "activity"
    assert updated_post.stars == 3
    assert updated_post.image_url is None
