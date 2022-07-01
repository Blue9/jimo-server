import uuid
from contextlib import contextmanager

import pytest
from shared.api.comment import (
    CreateCommentRequest,
    Comment,
    CommentPage,
    LikeCommentResponse,
)
from shared.models.models import (
    UserRow,
    PlaceRow,
    PostRow,
    UserRelationRow,
    UserRelationType,
)
from sqlalchemy import select

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
    user_a = UserRow(id=USER_A_ID, uid="a", username="a", first_name="a", last_name="a")
    user_b = UserRow(id=USER_B_ID, uid="b", username="b", first_name="b", last_name="b")
    session.add(user_a)
    session.add(user_b)
    await session.commit()

    place = PlaceRow(name="place_one", latitude=0, longitude=0)
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
        content="",
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


async def test_create_comment_regular_post(client):
    comment_content = "Nice"
    create_comment_request = CreateCommentRequest(post_id=USER_A_POST_ID, content=comment_content)
    with request_as(uid="b"):
        response = await client.post("/comments", data=create_comment_request.json())
        assert response.status_code == 200
        parsed = Comment.parse_obj(response.json())
        assert parsed.user.username == "b"
        assert parsed.post_id == USER_A_POST_ID
        assert parsed.content == comment_content
        assert parsed.like_count == 0
        assert not parsed.liked


async def test_create_comment_blocked_post(session, client):
    comment_content = "Nice"
    create_comment_request = CreateCommentRequest(post_id=USER_A_POST_ID, content=comment_content)
    # User A blocks user B
    session.add(
        UserRelationRow(
            from_user_id=USER_A_ID,
            to_user_id=USER_B_ID,
            relation=UserRelationType.blocked,
        )
    )
    await session.commit()

    with request_as(uid="b"):
        response = await client.post("/comments", data=create_comment_request.json())
        assert response.status_code == 404


async def test_create_comment_deleted_post(session, client):
    comment_content = "Nice"
    create_comment_request = CreateCommentRequest(post_id=USER_A_POST_ID, content=comment_content)
    # User A deleted their post
    post = (await session.execute(select(PostRow).where(PostRow.id == USER_A_POST_ID))).scalars().first()
    post.deleted = True
    await session.commit()

    with request_as(uid="b"):
        response = await client.post("/comments", data=create_comment_request.json())
        assert response.status_code == 404


async def test_get_comments_regular_post(client):
    # First create three comments and delete 1
    with request_as(uid="b"):
        response_1 = await client.post(
            "/comments",
            data=CreateCommentRequest(post_id=USER_A_POST_ID, content="1").json(),
        )
        response_2 = await client.post(
            "/comments",
            data=CreateCommentRequest(post_id=USER_A_POST_ID, content="2").json(),
        )
        response_3 = await client.post(
            "/comments",
            data=CreateCommentRequest(post_id=USER_A_POST_ID, content="3").json(),
        )
        comment_1 = response_1.json()
        comment_2 = response_2.json()
        comment_3 = response_3.json()
        response = await client.delete(f"/comments/{comment_3['commentId']}")
        assert response.status_code == 200

    with request_as(uid="b"):
        response = await client.get(f"/posts/{USER_A_POST_ID}/comments")
        parsed = CommentPage.parse_obj(response.json())
        assert response.status_code == 200
        assert len(parsed.comments) == 2
        assert parsed.comments[0] == Comment.parse_obj(comment_1)
        assert parsed.comments[1] == Comment.parse_obj(comment_2)


async def test_get_comments_blocked_post(session, client):
    # User A blocks user B
    session.add(
        UserRelationRow(
            from_user_id=USER_A_ID,
            to_user_id=USER_B_ID,
            relation=UserRelationType.blocked,
        )
    )
    await session.commit()

    with request_as(uid="b"):
        response = await client.get(f"/posts/{USER_A_POST_ID}/comments")
        assert response.status_code == 404


async def test_get_comments_deleted_post(session, client):
    # User A deleted their post
    post = (await session.execute(select(PostRow).where(PostRow.id == USER_A_POST_ID))).scalars().first()
    post.deleted = True
    await session.commit()

    with request_as(uid="b"):
        response = await client.get(f"/posts{USER_A_POST_ID}/comments")
        assert response.status_code == 404


async def test_delete_comment_regular_post(session, client):
    # First create three comments and delete 1
    with request_as(uid="b"):
        b_response = await client.post(
            "/comments",
            data=CreateCommentRequest(post_id=USER_A_POST_ID, content="1").json(),
        )
        b_comment = b_response.json()
    with request_as(uid="a"):
        a_response = await client.post(
            "/comments",
            data=CreateCommentRequest(post_id=USER_A_POST_ID, content="2").json(),
        )
        a_comment = a_response.json()
    with request_as(uid="b"):
        deleted_response = await client.post(
            "/comments",
            data=CreateCommentRequest(post_id=USER_A_POST_ID, content="3").json(),
        )
        deleted = deleted_response.json()
        response = await client.delete(f"/comments/{deleted['commentId']}")
        assert response.status_code == 200

    with request_as(uid="b"):
        # Delete my comment
        response = await client.delete(f"/comments/{b_comment['commentId']}")
        assert response.status_code == 200, "Should be able to delete your own comment"
        # Delete someone else's comment
        response = await client.delete(f"/comments/{a_comment['commentId']}")
        assert response.status_code == 403, "Should not be able to delete someone else's comment"
        # Delete a deleted comment
        response = await client.delete(f"/comments/{deleted['commentId']}")
        assert response.status_code == 404, "Should not be able to delete already deleted comment"

    with request_as(uid="b"):
        response = await client.get(f"/posts/{USER_A_POST_ID}/comments")
        parsed = CommentPage.parse_obj(response.json())
        assert len(parsed.comments) == 1
        assert parsed.comments[0] == Comment.parse_obj(a_comment)


async def test_delete_comment_blocked_post(session, client):
    # First create one comment
    with request_as(uid="b"):
        b_response = await client.post(
            "/comments",
            data=CreateCommentRequest(post_id=USER_A_POST_ID, content="1").json(),
        )
        b_comment = b_response.json()
    # User A blocks user B
    session.add(
        UserRelationRow(
            from_user_id=USER_A_ID,
            to_user_id=USER_B_ID,
            relation=UserRelationType.blocked,
        )
    )
    await session.commit()
    with request_as(uid="b"):
        response = await client.delete(f"/comments/{b_comment['commentId']}")
        assert response.status_code == 200


async def test_delete_comment_deleted_post(session, client):
    # First create one comment
    with request_as(uid="b"):
        b_response = await client.post(
            "/comments",
            data=CreateCommentRequest(post_id=USER_A_POST_ID, content="1").json(),
        )
        b_comment = b_response.json()
    # User A deleted their post
    post = (await session.execute(select(PostRow).where(PostRow.id == USER_A_POST_ID))).scalars().first()
    post.deleted = True
    await session.commit()
    with request_as(uid="b"):
        response = await client.delete(f"/comments/{b_comment['commentId']}")
        assert response.status_code == 404


async def test_delete_comment_on_my_post(session, client):
    # First create one comment
    with request_as(uid="b"):
        b_response = await client.post(
            "/comments",
            data=CreateCommentRequest(post_id=USER_A_POST_ID, content="1").json(),
        )
        b_comment = b_response.json()
    # User A deletes the comment
    with request_as(uid="a"):
        delete_comment_response = await client.delete(f"/comments/{b_comment['commentId']}")
        assert delete_comment_response.status_code == 200
        get_comments_response = (await client.get(f"/posts/{USER_A_POST_ID}/comments")).json()
        parsed = CommentPage.parse_obj(get_comments_response)
        assert len(parsed.comments) == 0
        assert parsed.cursor is None


async def test_like_comment(client):
    # First create one comment
    with request_as(uid="b"):
        b_response = await client.post(
            "/comments",
            data=CreateCommentRequest(post_id=USER_A_POST_ID, content="1").json(),
        )
        b_comment = b_response.json()
    # Like comment
    with request_as(uid="a"):
        like_comment_response = await client.post(f"/comments/{b_comment['commentId']}/likes")
        assert like_comment_response.status_code == 200
        parsed = LikeCommentResponse.parse_obj(like_comment_response.json())
        assert parsed.likes == 1
    # Like comment again
    with request_as(uid="a"):
        like_comment_response = await client.post(f"/comments/{b_comment['commentId']}/likes")
        assert like_comment_response.status_code == 200
        parsed = LikeCommentResponse.parse_obj(like_comment_response.json())
        assert parsed.likes == 1
    # Like comment other user
    with request_as(uid="b"):
        like_comment_response = await client.post(f"/comments/{b_comment['commentId']}/likes")
        assert like_comment_response.status_code == 200
        parsed = LikeCommentResponse.parse_obj(like_comment_response.json())
        assert parsed.likes == 2
    # Get comments, make sure like count matches
    with request_as(uid="b"):
        response = await client.get(f"/posts/{USER_A_POST_ID}/comments")
        comment_page = CommentPage.parse_obj(response.json())
        assert len(comment_page.comments) == 1
        assert comment_page.cursor is None
        assert comment_page.comments[0].like_count == 2


async def test_unlike_comment(client):
    # First create one comment
    with request_as(uid="b"):
        b_response = await client.post(
            "/comments",
            data=CreateCommentRequest(post_id=USER_A_POST_ID, content="1").json(),
        )
        b_comment = b_response.json()
    # Like comment
    with request_as(uid="a"):
        like_comment_response = await client.post(f"/comments/{b_comment['commentId']}/likes")
        assert like_comment_response.status_code == 200
        parsed = LikeCommentResponse.parse_obj(like_comment_response.json())
        assert parsed.likes == 1
    # Unlike comment
    with request_as(uid="a"):
        like_comment_response = await client.delete(f"/comments/{b_comment['commentId']}/likes")
        assert like_comment_response.status_code == 200
        parsed = LikeCommentResponse.parse_obj(like_comment_response.json())
        assert parsed.likes == 0


async def test_like_unlike_comment_blocked_post(session, client):
    # First create one comment
    with request_as(uid="b"):
        b_response = await client.post(
            "/comments",
            data=CreateCommentRequest(post_id=USER_A_POST_ID, content="1").json(),
        )
        b_comment_id = b_response.json()["commentId"]
    # User A blocks user B
    session.add(
        UserRelationRow(
            from_user_id=USER_A_ID,
            to_user_id=USER_B_ID,
            relation=UserRelationType.blocked,
        )
    )
    await session.commit()
    with request_as(uid="b"):
        response = await client.post(f"/comments/{b_comment_id}/likes")
        assert response.status_code == 200
    with request_as(uid="b"):
        response = await client.delete(f"/comments/{b_comment_id}/likes")
        assert response.status_code == 200


async def test_like_unlike_comment_deleted_post(session, client):
    # First create one comment
    with request_as(uid="b"):
        b_response = await client.post(
            "/comments",
            data=CreateCommentRequest(post_id=USER_A_POST_ID, content="1").json(),
        )
        b_comment_id = b_response.json()["commentId"]
    # User A deleted their post
    post = (await session.execute(select(PostRow).where(PostRow.id == USER_A_POST_ID))).scalars().first()
    post.deleted = True
    await session.commit()
    with request_as(uid="b"):
        response = await client.post(f"/comments/{b_comment_id}/likes")
        assert response.status_code == 404
    with request_as(uid="b"):
        response = await client.delete(f"/comments/{b_comment_id}/likes")
        assert response.status_code == 404
