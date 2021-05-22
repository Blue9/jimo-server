import uuid
from contextlib import contextmanager

from fastapi.testclient import TestClient

from app.controllers.firebase import get_firebase_user, FirebaseUser
from app.db.database import get_session, engine
from app.main import app as main_app
from app.models import models
from tests.mock_firebase import MockFirebaseAdmin
from tests.utils import init_db, reset_db

client = TestClient(main_app)

USER_A_POST_ID = uuid.uuid4()
USER_B_POST_ID = uuid.uuid4()


def setup_module():
    init_db(engine)
    with get_session() as session:
        user_a = models.User(uid="a", username="a", first_name="a", last_name="a")
        user_b = models.User(uid="b", username="b", first_name="b", last_name="b")
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


@contextmanager
def request_as(uid: str):
    main_app.dependency_overrides[get_firebase_user] = lambda: FirebaseUser(MockFirebaseAdmin(), uid=uid)
    yield
    main_app.dependency_overrides = {}


def test_basic_blocking():
    block = lambda username: f"/users/{username}/block"  # noqa(E731)

    # Blocking other user is fine
    with request_as(uid="a"):
        response = client.post(block("b"))
        print(response.json())
        assert response.status_code == 200
        assert response.json()["success"]

    # Blocking someone who has blocked you doesn't work
    with request_as(uid="b"):
        response = client.post(block("a"))
        assert response.status_code == 404

    # Blocking yourself doesn't work
    with request_as(uid="b"):
        response = client.post(block("b"))
        assert response.status_code == 400

    # Can't view someone who blocked you
    with request_as(uid="b"):
        response = client.get("/users/a")
        assert response.status_code == 404
        response = client.get("/users/a/posts")
        assert response.status_code == 404

    # Unblocking works fine
    with request_as(uid="a"):
        response = client.post("/users/b/unblock")
        assert response.status_code == 200


def teardown_module():
    reset_db(engine)
