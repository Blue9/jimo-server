import uuid
from contextlib import contextmanager

import pytest
from fastapi import FastAPI
from starlette.testclient import TestClient

from app import schemas
from app.controllers.firebase import get_firebase_user, FirebaseUser
from app.db.database import engine, get_session
from app.main import app as main_app
from app.models import models
from tests.mock_firebase import MockFirebaseAdmin
from tests.utils import init_db, reset_db

USER_A_ID = uuid.uuid4()
USER_B_ID = uuid.uuid4()
USER_A_POST_ID = uuid.uuid4()
USER_B_POST_ID = uuid.uuid4()


@pytest.fixture
def app() -> FastAPI:
    return main_app


def setup_module():
    init_db(engine)


def teardown_module():
    reset_db(engine)


def setup_function():
    with get_session() as session:
        user_a = models.User(id=USER_A_ID, uid="a", username="a", first_name="a", last_name="a")
        user_b = models.User(id=USER_B_ID, uid="b", username="b", first_name="b", last_name="b")
        session.add(user_a)
        session.add(user_b)
        session.commit()

        place = models.Place(name="place_one", latitude=0, longitude=0)
        session.add(place)
        session.commit()

        user_a_post = models.Post(
            id=USER_A_POST_ID,
            user_id=user_a.id,
            place_id=place.id,
            category="food",
            content=""
        )
        user_b_post = models.Post(
            id=USER_B_POST_ID,
            user_id=user_b.id,
            place_id=place.id,
            category="food",
            content=""
        )
        session.add(user_a_post)
        session.add(user_b_post)
        session.commit()


def teardown_function():
    with get_session() as session:
        session.query(models.User).delete()
        session.query(models.Waitlist).delete()
        session.query(models.Invite).delete()
        session.query(models.Place).delete()
        session.commit()


@contextmanager
def request_as(app: FastAPI, uid: str):
    app.dependency_overrides[get_firebase_user] = lambda: FirebaseUser(MockFirebaseAdmin(), uid=uid)
    yield
    app.dependency_overrides = {}


def test_create_comment_regular_post(app: FastAPI):
    client = TestClient(app)
    comment_content = "Nice"
    create_comment_request = schemas.comment.CreateCommentRequest(post_id=USER_A_POST_ID, content=comment_content)
    with request_as(app, uid="b"):
        response = client.post("/comments", data=create_comment_request.json())
        assert response.status_code == 200
        parsed = schemas.comment.Comment.parse_obj(response.json())
        assert parsed.user.username == "b"
        assert parsed.post_id == USER_A_POST_ID
        assert parsed.content == comment_content
        assert parsed.like_count == 0
        assert not parsed.liked


def test_create_comment_blocked_post(app: FastAPI):
    client = TestClient(app)
    comment_content = "Nice"
    create_comment_request = schemas.comment.CreateCommentRequest(post_id=USER_A_POST_ID, content=comment_content)
    # User A blocks user B
    with get_session() as session:
        session.add(
            models.UserRelation(from_user_id=USER_A_ID, to_user_id=USER_B_ID, relation=models.UserRelationType.blocked))
        session.commit()

    with request_as(app, uid="b"):
        response = client.post("/comments", data=create_comment_request.json())
        assert response.status_code == 404


def test_create_comment_deleted_post(app: FastAPI):
    client = TestClient(app)
    comment_content = "Nice"
    create_comment_request = schemas.comment.CreateCommentRequest(post_id=USER_A_POST_ID, content=comment_content)
    # User A deleted their post
    with get_session() as session:
        post = session.query(models.Post).filter_by(id=USER_A_POST_ID).first()
        post.deleted = True
        session.commit()

    with request_as(app, uid="b"):
        response = client.post("/comments", data=create_comment_request.json())
        assert response.status_code == 404


def test_get_comments_regular_post(app: FastAPI):
    client = TestClient(app)
    # First create three comments and delete 1
    with request_as(app, uid="b"):
        comment_1 = client.post(
            "/comments", data=schemas.comment.CreateCommentRequest(post_id=USER_A_POST_ID, content="1").json()).json()
        comment_2 = client.post(
            "/comments", data=schemas.comment.CreateCommentRequest(post_id=USER_A_POST_ID, content="2").json()).json()
        comment_3 = client.post(
            "/comments", data=schemas.comment.CreateCommentRequest(post_id=USER_A_POST_ID, content="3").json()).json()
        response = client.delete(f"/comments/{comment_3['commentId']}")
        assert response.status_code == 200

    with request_as(app, uid="b"):
        response = client.get(f"/posts/{USER_A_POST_ID}/comments")
        parsed = schemas.comment.CommentPage.parse_obj(response.json())
        assert response.status_code == 200
        assert len(parsed.comments) == 2
        assert parsed.comments[0] == schemas.comment.Comment.parse_obj(comment_2)
        assert parsed.comments[1].dict() == schemas.comment.Comment.parse_obj(comment_1)


def test_get_comments_blocked_post(app: FastAPI):
    client = TestClient(app)
    # User A blocks user B
    with get_session() as session:
        session.add(
            models.UserRelation(from_user_id=USER_A_ID, to_user_id=USER_B_ID, relation=models.UserRelationType.blocked))
        session.commit()

    with request_as(app, uid="b"):
        response = client.get(f"/posts/{USER_A_POST_ID}/comments")
        assert response.status_code == 404


def test_get_comments_deleted_post(app: FastAPI):
    client = TestClient(app)
    # User A deleted their post
    with get_session() as session:
        post = session.query(models.Post).filter_by(id=USER_A_POST_ID).first()
        post.deleted = True
        session.commit()

    with request_as(app, uid="b"):
        response = client.get(f"/posts{USER_A_POST_ID}/comments")
        assert response.status_code == 404


def test_delete_comment_regular_post(app: FastAPI):
    client = TestClient(app)
    # First create three comments and delete 1
    with request_as(app, uid="b"):
        b_comment = client.post(
            "/comments", data=schemas.comment.CreateCommentRequest(post_id=USER_A_POST_ID, content="1").json()).json()
    with request_as(app, uid="a"):
        a_comment = client.post(
            "/comments", data=schemas.comment.CreateCommentRequest(post_id=USER_A_POST_ID, content="2").json()).json()
    with request_as(app, uid="b"):
        deleted = client.post(
            "/comments", data=schemas.comment.CreateCommentRequest(post_id=USER_A_POST_ID, content="3").json()).json()
        response = client.delete(f"/comments/{deleted['commentId']}")
        assert response.status_code == 200

    with request_as(app, uid="b"):
        # Delete my comment
        response = client.delete(f"/comments/{b_comment['commentId']}")
        assert response.status_code == 200, "Should be able to delete your own comment"
        # Delete someone else's comment
        response = client.delete(f"/comments/{a_comment['commentId']}")
        assert response.status_code == 403, "Should not be able to delete someone else's comment"
        # Delete a deleted comment
        response = client.delete(f"/comments/{deleted['commentId']}")
        assert response.status_code == 404, "Should not be able to delete already deleted comment"

    with request_as(app, uid="b"):
        response = client.get(f"/posts/{USER_A_POST_ID}/comments").json()
        parsed = schemas.comment.CommentPage.parse_obj(response)
        assert len(parsed.comments) == 1
        assert parsed.comments[0] == schemas.comment.Comment.parse_obj(a_comment)


def test_delete_comment_blocked_post(app: FastAPI):
    client = TestClient(app)
    # First create one comment
    with request_as(app, uid="b"):
        b_comment = client.post(
            "/comments", data=schemas.comment.CreateCommentRequest(post_id=USER_A_POST_ID, content="1").json()).json()
    # User A blocks user B
    with get_session() as session:
        session.add(
            models.UserRelation(from_user_id=USER_A_ID, to_user_id=USER_B_ID, relation=models.UserRelationType.blocked))
        session.commit()
    with request_as(app, uid="b"):
        response = client.delete(f"/comments/{b_comment['commentId']}")
        assert response.status_code == 200


def test_delete_comment_deleted_post(app: FastAPI):
    client = TestClient(app)
    # First create one comment
    with request_as(app, uid="b"):
        b_comment = client.post(
            "/comments", data=schemas.comment.CreateCommentRequest(post_id=USER_A_POST_ID, content="1").json()).json()
    # User A deleted their post
    with get_session() as session:
        post = session.query(models.Post).filter_by(id=USER_A_POST_ID).first()
        post.deleted = True
        session.commit()
    with request_as(app, uid="b"):
        response = client.delete(f"/comments/{b_comment['commentId']}")
        assert response.status_code == 404


def test_delete_comment_on_my_post(app: FastAPI):
    client = TestClient(app)
    # First create one comment
    with request_as(app, uid="b"):
        b_comment = client.post(
            "/comments", data=schemas.comment.CreateCommentRequest(post_id=USER_A_POST_ID, content="1").json()).json()
    # User A deletes the comment
    with request_as(app, uid="a"):
        delete_comment_response = client.delete(f"/comments/{b_comment['commentId']}")
        assert delete_comment_response.status_code == 200
        get_comments_response = client.get(f"/posts/{USER_A_POST_ID}/comments").json()
        parsed = schemas.comment.CommentPage.parse_obj(get_comments_response)
        assert len(parsed.comments) == 0
        assert parsed.cursor is None


def test_like_comment(app: FastAPI):
    client = TestClient(app)
    # First create one comment
    with request_as(app, uid="b"):
        b_comment = client.post(
            "/comments", data=schemas.comment.CreateCommentRequest(post_id=USER_A_POST_ID, content="1").json()).json()
    # Like comment
    with request_as(app, uid="a"):
        like_comment_response = client.post(f"/comments/{b_comment['commentId']}/likes")
        assert like_comment_response.status_code == 200
        parsed = schemas.comment.LikeCommentResponse.parse_obj(like_comment_response.json())
        assert parsed.likes == 1
    # Like comment again
    with request_as(app, uid="a"):
        like_comment_response = client.post(f"/comments/{b_comment['commentId']}/likes")
        assert like_comment_response.status_code == 200
        parsed = schemas.comment.LikeCommentResponse.parse_obj(like_comment_response.json())
        assert parsed.likes == 1
    # Like comment other user
    with request_as(app, uid="b"):
        like_comment_response = client.post(f"/comments/{b_comment['commentId']}/likes")
        assert like_comment_response.status_code == 200
        parsed = schemas.comment.LikeCommentResponse.parse_obj(like_comment_response.json())
        assert parsed.likes == 2
    # Get comments, make sure like count matches
    with request_as(app, uid="b"):
        response = client.get(f"/posts/{USER_A_POST_ID}/comments").json()
        comment_page = schemas.comment.CommentPage.parse_obj(response)
        assert len(comment_page.comments) == 1
        assert comment_page.cursor is None
        assert comment_page.comments[0].like_count == 2


def test_unlike_comment(app: FastAPI):
    client = TestClient(app)
    # First create one comment
    with request_as(app, uid="b"):
        b_comment = client.post(
            "/comments", data=schemas.comment.CreateCommentRequest(post_id=USER_A_POST_ID, content="1").json()).json()
    # Like comment
    with request_as(app, uid="a"):
        like_comment_response = client.post(f"/comments/{b_comment['commentId']}/likes")
        assert like_comment_response.status_code == 200
        parsed = schemas.comment.LikeCommentResponse.parse_obj(like_comment_response.json())
        assert parsed.likes == 1
    # Unlike comment
    with request_as(app, uid="a"):
        like_comment_response = client.delete(f"/comments/{b_comment['commentId']}/likes")
        assert like_comment_response.status_code == 200
        parsed = schemas.comment.LikeCommentResponse.parse_obj(like_comment_response.json())
        assert parsed.likes == 0


def test_like_unlike_comment_blocked_post(app: FastAPI):
    client = TestClient(app)
    # First create one comment
    with request_as(app, uid="b"):
        b_comment = client.post(
            "/comments", data=schemas.comment.CreateCommentRequest(post_id=USER_A_POST_ID, content="1").json()).json()
    # User A blocks user B
    with get_session() as session:
        session.add(
            models.UserRelation(from_user_id=USER_A_ID, to_user_id=USER_B_ID, relation=models.UserRelationType.blocked))
        session.commit()
    with request_as(app, uid="b"):
        response = client.post(f"/comments/{b_comment['commentId']}/likes")
        assert response.status_code == 200
    with request_as(app, uid="b"):
        response = client.delete(f"/comments/{b_comment['commentId']}/likes")
        assert response.status_code == 200


def test_like_unlike_comment_deleted_post(app: FastAPI):
    client = TestClient(app)
    # First create one comment
    with request_as(app, uid="b"):
        b_comment = client.post(
            "/comments", data=schemas.comment.CreateCommentRequest(post_id=USER_A_POST_ID, content="1").json()).json()
    # User A deleted their post
    with get_session() as session:
        post = session.query(models.Post).filter_by(id=USER_A_POST_ID).first()
        post.deleted = True
        session.commit()
    with request_as(app, uid="b"):
        response = client.post(f"/comments/{b_comment['commentId']}/likes")
        assert response.status_code == 404
    with request_as(app, uid="b"):
        response = client.delete(f"/comments/{b_comment['commentId']}/likes")
        assert response.status_code == 404
