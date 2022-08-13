import typing

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.types import UserId
from app.core.database.models import UserPrefsRow

UserPrefsQueryT = typing.TypeVar("UserPrefsQueryT", bound="UserPrefsQuery")


class UserPrefsQuery:
    def __init__(self: UserPrefsQueryT):
        self.query = sa.select(UserPrefsRow)

    def user_id(self: UserPrefsQueryT, user_id: UserId) -> UserPrefsQueryT:
        self.query = self.query.where(UserPrefsRow.user_id == user_id)
        return self

    async def execute_one(self: UserPrefsQueryT, session: AsyncSession) -> typing.Optional[UserPrefsRow]:
        result = await session.execute(self.query)
        return result.scalars().first()
