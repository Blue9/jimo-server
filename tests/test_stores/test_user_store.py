import uuid

import pytest
import pytest_asyncio
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database.models import UserRow
from app.features.users.user_store import UserStore

pytestmark = pytest.mark.asyncio
USER_A_ID = uuid.uuid4()
USER_B_ID = uuid.uuid4()
USER_A_POST_ID = uuid.uuid4()
USER_B_POST_ID = uuid.uuid4()


@pytest_asyncio.fixture(autouse=True, scope="function")
async def setup_fixture(session):
    user_a = UserRow(id=USER_A_ID, uid="a", username="a", first_name="a", last_name="a")
    user_b = UserRow(id=USER_B_ID, uid="b", username="b", first_name="b", last_name="b")
    session.add(user_a)
    session.add(user_b)
    await session.commit()


@pytest.fixture(scope="function")
def user_store(session: AsyncSession) -> UserStore:
    return UserStore(db=session)


async def test_is_uid_taken(session):
    user_store = UserStore(db=session)
    assert await user_store.user_exists(uid="a") is True
    assert await user_store.user_exists(uid="b") is True
    assert await user_store.user_exists(uid="c") is False


async def test_is_username_taken(session):
    user_store = UserStore(db=session)
    assert await user_store.user_exists(username="a") is True
    assert await user_store.user_exists(username="b") is True
    assert await user_store.user_exists(username="c") is False


async def test_soft_delete_user(session: AsyncSession, user_store: UserStore):
    await user_store.soft_delete_user(USER_A_ID)
    assert await user_store.get_user(USER_A_ID) is None
    assert await user_store.get_user(USER_B_ID) is not None

    # Make sure the db is updated
    result = await session.execute(sa.select(UserRow).where(UserRow.id == USER_A_ID))
    rows = result.scalars().all()
    assert len(rows) == 1
    assert rows[0].id == USER_A_ID
    assert rows[0].deleted


async def test_hard_delete_user(session: AsyncSession, user_store: UserStore):
    await user_store.hard_delete_user(USER_A_ID)
    assert await user_store.get_user(USER_A_ID) is None
    assert await user_store.get_user(USER_B_ID) is not None

    # Make sure the db is updated
    result = await session.execute(sa.select(UserRow).where(UserRow.id == USER_A_ID))
    rows = result.scalars().all()
    assert len(rows) == 0
