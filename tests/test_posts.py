import uuid
from contextlib import contextmanager
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from fastapi.encoders import jsonable_encoder

from app.core.database.models import UserRow, PlaceRow, ImageUploadRow, PostRow
from app.core.firebase import get_firebase_user, FirebaseUser
from app.features.places.entities import Location
from app.features.posts.entities import PostWithoutLikeSaveStatus
from app.features.posts.types import CreatePostRequest, MaybeCreatePlaceWithMetadataRequest
from app.main import app as main_app
from tests.mock_firebase import MockFirebaseAdmin

pytestmark = pytest.mark.asyncio
USER_A_ID = uuid.uuid4()
USER_B_ID = uuid.uuid4()
IMAGE_A_ID = uuid.uuid4()
USER_A_POST_ID = uuid.uuid4()
USER_B_POST_ID = uuid.uuid4()

PLACE_ONE_ID = uuid.uuid4()
PLACE_TWO_ID = uuid.uuid4()


@pytest_asyncio.fixture(autouse=True, scope="function")
async def setup_fixture(session):
    user_a = UserRow(id=USER_A_ID, uid="a", username="a", first_name="a", last_name="a")
    user_b = UserRow(id=USER_B_ID, uid="b", username="b", first_name="b", last_name="b")
    session.add(user_a)
    session.add(user_b)
    await session.commit()

    place_one = PlaceRow(id=PLACE_ONE_ID, name="place_one", latitude=0, longitude=0)
    place_two = PlaceRow(id=PLACE_TWO_ID, name="place_two", latitude=10, longitude=10)
    session.add(place_one)
    session.add(place_two)
    await session.commit()

    await session.refresh(user_a)
    await session.refresh(user_b)
    session.add(place_one)
    session.add(place_two)

    image_a = ImageUploadRow(
        id=IMAGE_A_ID,
        user_id=USER_A_ID,
        blob_name="blob-name",
        url="public-url",
    )
    session.add(image_a)
    await session.commit()

    user_a_post = PostRow(
        id=USER_A_POST_ID,
        user_id=USER_A_ID,
        place_id=PLACE_ONE_ID,
        category="food",
        content="",
        image_id=IMAGE_A_ID,
    )
    user_b_post = PostRow(
        id=USER_B_POST_ID,
        user_id=USER_B_ID,
        place_id=PLACE_TWO_ID,
        category="food",
        content="",
    )
    session.add(user_a_post)
    session.add(user_b_post)
    await session.commit()


@contextmanager
def request_as(uid: str):
    firebase_user = FirebaseUser(MockFirebaseAdmin(), uid=uid)
    main_app.dependency_overrides[get_firebase_user] = lambda: firebase_user
    yield firebase_user
    main_app.dependency_overrides = {}


async def test_update_post(client):
    # Update a post
    request = CreatePostRequest(
        place_id=PLACE_ONE_ID,
        place=None,
        category="activity",
        content="new content",
        image_id=IMAGE_A_ID,
    )
    with request_as("a"):
        response = await client.put(f"/posts/{USER_A_POST_ID}", json=jsonable_encoder(request))
    assert response.status_code == 200
    post = PostWithoutLikeSaveStatus.parse_obj(response.json())
    assert post.place.id == PLACE_ONE_ID
    assert post.category == "activity"
    assert post.content == "new content"
    assert post.image_url is not None

    # Update non-existent post
    with request_as("a"):
        response = await client.put(f"/posts/{uuid.uuid4()}", json=jsonable_encoder(request))
    assert response.status_code == 404

    # Update someone else's post
    with request_as("b"):
        response = await client.put(f"/posts/{USER_A_POST_ID}", json=jsonable_encoder(request))
    assert response.status_code == 403

    # Update using place request
    request = CreatePostRequest(
        place_id=None,
        place=MaybeCreatePlaceWithMetadataRequest(name="place_two", location=Location(latitude=10, longitude=10)),
        category="shopping",
        content="new content",
        image_id=IMAGE_A_ID,
    )
    with request_as("a"):
        response = await client.put(f"/posts/{USER_A_POST_ID}", json=jsonable_encoder(request))
    assert response.status_code == 200
    post = PostWithoutLikeSaveStatus.parse_obj(response.json())
    assert post.place.id == PLACE_TWO_ID
    assert post.category == "shopping"
    assert post.content == "new content"

    # Update image ID -> None, make sure old image is deleted
    request = CreatePostRequest(
        place_id=None,
        place=MaybeCreatePlaceWithMetadataRequest(name="place_two", location=Location(latitude=10, longitude=10)),
        category="shopping",
        content="new content",
        image_id=None,
    )
    with request_as("a") as firebase_user:
        firebase_user.shared_firebase.delete_image = AsyncMock()
        main_app.dependency_overrides[get_firebase_user] = lambda: firebase_user
        response = await client.put(f"/posts/{USER_A_POST_ID}", json=jsonable_encoder(request))
        firebase_user.shared_firebase.delete_image.assert_called_once()
    assert response.status_code == 200
    post = PostWithoutLikeSaveStatus.parse_obj(response.json())
    assert post.place.id == PLACE_TWO_ID
    assert post.category == "shopping"
    assert post.content == "new content"
    assert post.image_url is None
