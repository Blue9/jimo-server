from typing import Optional

import sqlalchemy as sa
from sqlalchemy import select, func, asc
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.places.entities import Location
from app.core.types import UserId, PostId, CursorId
from app.core.database.models import (
    PlaceRow,
    PostRow,
    UserRow,
    UserRelationRow,
    UserRelationType,
)


class FeedStore:
    def __init__(self, db: AsyncSession):
        self.db = db

    @staticmethod
    def _followed_users_subquery(user_id: UserId) -> sa.sql.Select:
        return select(UserRelationRow.to_user_id).where(
            UserRelationRow.from_user_id == user_id,
            UserRelationRow.relation == UserRelationType.following,
        )

    async def get_feed_ids(self, user_id: UserId, cursor: Optional[CursorId] = None, limit: int = 10) -> list[PostId]:
        """Get the user's feed, returning a list of post ids."""
        query = self._feed_ids_query(user_id)
        if cursor:
            query = query.where(PostRow.id < cursor)
        result = await self.db.execute(query.order_by(PostRow.id.desc()).limit(limit))
        return result.scalars().all()

    def _feed_ids_query(self, user_id: UserId) -> sa.sql.Select:
        followed_users_subquery = self._followed_users_subquery(user_id)
        return (
            select(PostRow.id)
            .where((PostRow.user_id == user_id) | PostRow.user_id.in_(followed_users_subquery))
            .where(~PostRow.deleted)
        )

    async def get_discover_feed_ids(
        self, user_id: UserId, location: Optional[Location] = None, limit: int = 100
    ) -> list[PostId]:
        """Get the user's discover feed."""
        query = (
            select(PostRow.id)
            .join(UserRow, UserRow.id == PostRow.user_id)
            .where(
                PostRow.user_id != user_id,
                PostRow.image_id.isnot(None),
                ~PostRow.deleted,
                ~UserRow.deleted,
            )
        )
        if location:
            center = func.ST_GeographyFromText(f"POINT({location.longitude} {location.latitude})")
            nearest_posts_subquery = (
                select(PostRow.id).join(PlaceRow).order_by(asc(func.ST_Distance(center, PlaceRow.location))).limit(1000)
            )
            query = query.where(PostRow.id.in_(nearest_posts_subquery))
        query = query.order_by(func.random()).limit(limit)
        result = await self.db.execute(query)
        return result.scalars().all()