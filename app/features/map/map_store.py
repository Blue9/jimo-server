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
from app.features.map.entities import MapPin, MapPinIcon, MapType
from app.features.places.entities import Location, Region, RectangularRegion
from app.core.types import PlaceId, Category, UserId


class MapStore:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_map(
        self,
        user_id: UserId,
        region: RectangularRegion,
        categories: list[Category],
        user_filter: MapType,
        user_ids: list[UserId] | None,
    ) -> list[MapPin]:
        query = base_map_query(region)
        if user_filter == "custom":
            if user_ids is None or len(user_ids) == 0:
                return []
            query = query.where(PostRow.user_id.in_(user_ids))
        elif user_filter == "me":
            query = query.where(PostRow.user_id == user_id)
        elif user_filter == "following":
            # TODO check if this is right
            query = query.join(
                UserRelationRow,
                (UserRelationRow.from_user_id == user_id)
                & (PostRow.user_id == UserRelationRow.to_user_id)
                & (UserRelationRow.relation == UserRelationType.following),
                isouter=True,
            ).where(UserRelationRow.to_user_id.is_not(None) | (PostRow.user_id == user_id))
        elif user_filter == "saved":
            saved_posts = sa.select(PostSaveRow.post_id).where(PostSaveRow.user_id == user_id)
            query = query.where(PostRow.id.in_(saved_posts))
        else:  # user_filter == "community"
            query = query.where((PostRow.image_id.is_not(None)) | (PostRow.content != ""))
        return await self._get_map(query, categories=categories, limit=500)

    async def get_community_map(
        self,
        region: Region,
        categories: Optional[list[Category]] = None,
        limit: int = 500,
    ) -> list[MapPin]:
        """Deprecated."""
        query = deprecated_base_map_query(region).where((PostRow.image_id.is_not(None)) | (PostRow.content != ""))
        return await self._get_map(query, categories=categories, limit=limit)

    async def get_friend_map(
        self,
        region: Region,
        user_id: UserId,
        categories: Optional[list[Category]] = None,
        limit: int = 500,
    ) -> list[MapPin]:
        """Deprecated."""
        friends = sa.select(UserRelationRow.to_user_id).where(
            UserRelationRow.from_user_id == user_id, UserRelationRow.relation == UserRelationType.following
        )
        query = deprecated_base_map_query(region).where((PostRow.user_id == user_id) | PostRow.user_id.in_(friends))
        return await self._get_map(query, categories=categories, limit=limit)

    async def get_saved_posts_map(
        self,
        region: Region,
        user_id: UserId,
        categories: Optional[list[Category]] = None,
        limit: int = 500,
    ) -> list[MapPin]:
        """Deprecated."""
        saved_posts = sa.select(PostSaveRow.post_id).where(PostSaveRow.user_id == user_id)
        query = deprecated_base_map_query(region).where(PostRow.id.in_(saved_posts))
        return await self._get_map(query, categories=categories, limit=limit)

    async def get_custom_map(
        self,
        region: Region,
        user_ids: list[UserId],
        categories: Optional[list[Category]] = None,
        limit: int = 500,
    ) -> list[MapPin]:
        """Deprecated."""
        query = deprecated_base_map_query(region).where(PostRow.user_id.in_(user_ids))
        return await self._get_map(query, categories=categories, limit=limit)

    async def _get_map(
        self, query: sa.sql.Select, categories: Optional[list[Category]] = None, limit: int = 500
    ) -> list[MapPin]:
        if categories and len(categories) < 6:
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


def base_map_query(region: RectangularRegion) -> sa.sql.Select:
    postgis_region = func.ST_MakeEnvelope(
        region.x_min,
        region.y_min,
        region.x_max,
        region.y_max,
        4326,
    )
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
        .where(func.ST_Intersects(postgis_region, PlaceRow.location))
        .where(~UserRow.deleted)
        .where(~PostRow.deleted)
    )
    return query


def deprecated_base_map_query(region: Region) -> sa.sql.Select:
    """
    Deprecated map query function. Use base_map_query() with a rectangular region instead.

    Reason: ST_Intersects is faster than ST_Distance and on iOS the MapKit view is given as a
    rectangular region.
    """
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
