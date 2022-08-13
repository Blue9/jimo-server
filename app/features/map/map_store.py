from typing import Optional

import sqlalchemy as sa
from sqlalchemy import func

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database.models import (
    PlaceRow,
    PostRow,
    ImageUploadRow,
    UserRow,
    UserRelationRow,
    UserRelationType,
    PostSaveRow,
)
from app.features.map.entities import MapPin, MapPinIcon
from app.features.places.entities import Location, Region
from app.core.types import PlaceId, Category, UserId


class MapStore:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_community_map(
        self,
        region: Region,
        categories: Optional[list[Category]] = None,
        limit: int = 500,
    ) -> list[MapPin]:
        query = base_map_query(region).where(PostRow.image_id.isnot(None) | (PostRow.content != ""))
        return await self._get_map(query, categories=categories, limit=limit)

    async def get_friend_map(
        self,
        region: Region,
        user_id: UserId,
        categories: Optional[list[Category]] = None,
        limit: int = 500,
    ) -> list[MapPin]:
        friends = sa.select(UserRelationRow.to_user_id).where(
            UserRelationRow.from_user_id == user_id, UserRelationRow.relation == UserRelationType.following
        )
        query = base_map_query(region).where((PostRow.user_id == user_id) | PostRow.user_id.in_(friends))
        return await self._get_map(query, categories=categories, limit=limit)

    async def get_saved_posts_map(
        self,
        region: Region,
        user_id: UserId,
        categories: Optional[list[Category]] = None,
        limit: int = 500,
    ) -> list[MapPin]:
        saved_posts = sa.select(PostSaveRow.post_id).where(PostSaveRow.user_id == user_id)
        query = base_map_query(region).where(PostRow.id.in_(saved_posts))
        return await self._get_map(query, categories=categories, limit=limit)

    async def get_custom_map(
        self,
        region: Region,
        user_ids: list[UserId],
        categories: Optional[list[Category]] = None,
        limit: int = 500,
    ) -> list[MapPin]:
        query = base_map_query(region).where(PostRow.user_id.in_(user_ids))
        return await self._get_map(query, categories=categories, limit=limit)

    async def _get_map(
        self, query: sa.sql.Select, categories: Optional[list[Category]] = None, limit: int = 500
    ) -> list[MapPin]:
        if categories:
            query = query.where(PostRow.category.in_(categories))
        query = query.order_by(PostRow.id.desc()).limit(limit)
        rows = (await self.db.execute(query)).all()
        pins = []
        pin_icons = dict()
        # TODO: clean up
        for row in rows:
            place_id: PlaceId = row[0]
            category: str = row[3]
            profile_picture_url: Optional[str] = row[4]
            if place_id not in pin_icons:
                pin_icons[place_id] = MapPinIcon(category=category, icon_url=profile_picture_url, num_posts=1)
            else:
                pin_icons[place_id].num_posts += 1
        added = set()
        for row in rows:
            place_id = row[0]
            latitude: float = row[1]
            longitude: float = row[2]
            if place_id in added:
                continue
            added.add(place_id)
            pins.append(
                MapPin(
                    place_id=place_id,
                    location=Location(latitude=latitude, longitude=longitude),
                    icon=pin_icons[place_id],
                )
            )
        return pins


def base_map_query(region: Region) -> sa.sql.Select:
    center = func.ST_GeographyFromText(f"POINT({region.longitude} {region.latitude})")
    query = (
        sa.select(
            PlaceRow.id,
            PlaceRow.latitude,
            PlaceRow.longitude,
            PostRow.category,
            ImageUploadRow.firebase_public_url,
            PostRow.user_id,
        )
        .select_from(PlaceRow)
        .join(PostRow, PostRow.place_id == PlaceRow.id)
        .join(UserRow, UserRow.id == PostRow.user_id)
        .join(
            ImageUploadRow,
            ImageUploadRow.id == UserRow.profile_picture_id,
            isouter=True,
        )
        .where(func.ST_Distance(center, PlaceRow.location) <= region.radius)
        .where(~UserRow.deleted)
        .where(~PostRow.deleted)
    )
    return query
