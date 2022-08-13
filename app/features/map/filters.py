from abc import ABC, abstractmethod
from typing import Optional

import sqlalchemy as sa
from sqlalchemy import select, values, column
from sqlalchemy.dialects import postgresql

from app.core.types import UserId
from app.core.database.models import (
    PostRow,
    PostSaveRow,
    UserRelationRow,
    UserRelationType,
)
from app.features.users.relation_query import UserRelationQuery


class MapFilter(ABC):
    @abstractmethod
    def apply(self, query: sa.sql.Select) -> sa.sql.Select:
        pass


class EveryoneFilter(MapFilter):
    def apply(self, query: sa.sql.Select) -> sa.sql.Select:
        return query.where(PostRow.image_id.isnot(None) | (PostRow.content != ""))


class SavedPostsFilter(MapFilter):
    def __init__(self, user_id: UserId):
        super().__init__()
        self.user_id = user_id

    def apply(self, query: sa.sql.Select) -> sa.sql.Select:
        return query.where(PostRow.id.in_(select(PostSaveRow.post_id).where(PostSaveRow.user_id == self.user_id)))


class FriendsFilter(MapFilter):
    def __init__(self, user_id: UserId):
        super().__init__()
        self.user_id = user_id

    def apply(self, query: sa.sql.Select) -> sa.sql.Select:
        friends = (
            UserRelationQuery(UserRelationType.following, query_entity=UserRelationRow.to_user_id)
            .from_user_id(self.user_id)
            .query
        )
        return query.where((PostRow.user_id == self.user_id) | PostRow.user_id.in_(friends))


class UserListFilter(MapFilter):
    def __init__(self, user_ids: list[UserId]):
        super().__init__()
        self.user_ids = user_ids

    def apply(self, query: sa.sql.Select) -> sa.sql.Select:
        if len(self.user_ids) > 100:
            return query.where(
                PostRow.user_id.in_(
                    values(column("user_id", postgresql.UUID), name="user_ids").data(
                        [(str(user_id),) for user_id in self.user_ids]
                    )
                )
            )
        return query.where(PostRow.user_id.in_(self.user_ids))


class CategoryFilter(MapFilter):
    def __init__(self, categories: Optional[list[str]]):
        self.categories = categories

    def apply(self, query: sa.sql.Select) -> sa.sql.Select:
        if not self.categories:
            return query
        return query.where(PostRow.category.in_(self.categories))
