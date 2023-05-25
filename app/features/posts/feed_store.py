from typing import Optional

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database.models import (
    PlaceRow,
    PostRow,
    UserRow,
    UserRelationRow,
    UserRelationType,
)
from app.core.types import UserId, PostId, CursorId
from app.features.places.entities import Location


class FeedStore:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_feed_ids(self, user_id: UserId, cursor: Optional[CursorId] = None, limit: int = 10) -> list[PostId]:
        """Get the user's feed, returning a list of post ids."""
        query = self._feed_ids_query(user_id)
        # Skip bib gourmand account in feed because we posted 3.4k times at once
        query = query.where(PostRow.user_id != "0183479c-a153-ab5f-f571-b1498a0957a4")
        if cursor:
            query = query.where(PostRow.id < cursor)
        result = await self.db.execute(query.order_by(PostRow.id.desc()).limit(limit))
        return result.scalars().all()  # type: ignore

    async def get_discover_feed_ids(
        self, user_id: UserId, location: Optional[Location] = None, limit: int = 100
    ) -> list[PostId]:
        """Get the user's discover feed. Most recent posts for now."""
        query = (
            sa.select(PostRow.id)
            .join(UserRow, UserRow.id == PostRow.user_id)
            .where(
                PostRow.user_id != user_id,
                (PostRow.image_id.is_not(None) | (PostRow.content != "")),
                ~PostRow.deleted,
                ~UserRow.deleted,
            )
            .order_by(PostRow.id.desc())
            .limit(limit)
        )
        # if location:
        #     center = sa.func.ST_GeographyFromText(f"POINT({location.longitude} {location.latitude})")
        #     nearest_posts_subquery = (
        #         sa.select(PostRow.id)
        #         .join(PlaceRow)
        #         .order_by(sa.asc(sa.func.ST_Distance(center, PlaceRow.location)))
        #         .limit(1000)
        #     )
        #     query = query.where(PostRow.id.in_(nearest_posts_subquery))
        result = await self.db.execute(query)
        return result.scalars().all()  # type: ignore

    def _feed_ids_query(self, user_id: UserId) -> sa.sql.Select:
        followed_users_subquery = self._followed_users_subquery(user_id)
        return (
            sa.select(PostRow.id)
            .where((PostRow.user_id == user_id) | PostRow.user_id.in_(followed_users_subquery))
            .where(~PostRow.deleted)
        )

    def _followed_users_subquery(self, user_id: UserId) -> sa.sql.Select:
        return sa.select(UserRelationRow.to_user_id).where(
            UserRelationRow.from_user_id == user_id,
            UserRelationRow.relation == UserRelationType.following,
        )
