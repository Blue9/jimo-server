from typing import Optional

import sqlalchemy as sa
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database.models import PlaceRow, PlaceDataRow, PostRow, UserRelationRow, UserRelationType, PostSaveRow
from app.core.types import UserId, PlaceId, PostId, Category
from app.features.places.entities import Region, AdditionalPlaceData, Place


class PlaceStore:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_place(self, place_id: PlaceId) -> Optional[Place]:
        query = sa.select(PlaceRow).where(PlaceRow.id == place_id)
        result = await self.db.execute(query)
        place_row = result.scalars().first()
        return Place.from_orm(place_row) if place_row else None

    async def find_or_create_place(
        self,
        name: str,
        latitude: float,
        longitude: float,
        search_radius_meters: float = 10,
    ) -> Place:
        """Try to find an existing place matching the given request, otherwise create a place and return it."""
        place = await self.find_place(name, latitude, longitude, search_radius_meters=search_radius_meters)
        if place is not None:
            return place
        return await self._create_place(name, latitude, longitude)

    async def find_place(
        self, name: str, latitude: float, longitude: float, search_radius_meters: float = 10
    ) -> Optional[Place]:
        query = sa.select(PlaceRow).where(PlaceRow.name == name)
        if search_radius_meters > 0:
            point = sa.func.ST_GeographyFromText(f"POINT({longitude} {latitude})")
            # TODO: Would like to use ST_DWithin but non-deterministically running into
            #  "no spatial operator found for 'st_dwithin'" (appears when running all tests at once (or test_posts and
            #  test_map) together, but it doesn't appear when running test_posts alone, will investigate later
            query = query.where(sa.func.ST_Distance(point, PlaceRow.location) < search_radius_meters)
        else:
            query = query.where(PlaceRow.latitude == latitude, PlaceRow.longitude == longitude)
        result = await self.db.execute(query)
        maybe_place = result.scalars().first()
        return Place.from_orm(maybe_place) if maybe_place else None

    async def update_place_metadata(
        self,
        user_id: UserId,
        place_id: PlaceId,
        region: Optional[Region] = None,
        additional_data: Optional[AdditionalPlaceData] = None,
    ) -> None:
        """Save the given place data to the database."""
        place_data = PlaceDataRow(place_id=place_id, user_id=user_id)
        if region:
            place_data.region_center_lat = region.latitude
            place_data.region_center_long = region.longitude
            place_data.radius_meters = region.radius
        if additional_data:
            place_data.additional_data = additional_data.dict()
        try:
            self.db.add(place_data)
            await self.db.commit()
        except IntegrityError:
            await self.db.rollback()

    async def get_community_posts(self, place_id: PlaceId, categories: Optional[list[Category]] = None) -> list[PostId]:
        # TODO: this should probably not be in place store
        query = (
            sa.select(PostRow.id)
            .where(PostRow.place_id == place_id, ~PostRow.deleted)
            .where(PostRow.image_id.isnot(None) | (PostRow.content != ""))
        )
        if categories:
            query = query.where(PostRow.category.in_(categories))
        result = await self.db.execute(query)
        post_ids = result.scalars().all()
        return post_ids

    async def get_friend_posts(
        self, place_id: PlaceId, user_id: UserId, categories: Optional[list[Category]] = None
    ) -> list[PostId]:
        # TODO: this should probably not be in place store
        friends = sa.select(UserRelationRow.to_user_id).where(
            UserRelationRow.from_user_id == user_id, UserRelationRow.relation == UserRelationType.following
        )
        query = (
            sa.select(PostRow.id)
            .where(PostRow.place_id == place_id, ~PostRow.deleted)
            .where((PostRow.user_id == user_id) | PostRow.user_id.in_(friends))
        )
        if categories:
            query = query.where(PostRow.category.in_(categories))
        result = await self.db.execute(query)
        post_ids = result.scalars().all()
        return post_ids

    async def get_saved_posts(
        self, place_id: PlaceId, user_id: UserId, categories: Optional[list[Category]] = None
    ) -> list[PostId]:
        # TODO: this should probably not be in place store
        query = (
            sa.select(PostRow.id)
            .where(PostRow.place_id == place_id, ~PostRow.deleted)
            .where(PostRow.id.in_(sa.select(PostSaveRow.post_id).where(PostSaveRow.user_id == user_id)))
        )
        if categories:
            query = query.where(PostRow.category.in_(categories))
        result = await self.db.execute(query)
        post_ids = result.scalars().all()
        return post_ids

    async def get_custom_posts(
        self, place_id: PlaceId, user_ids: list[UserId], categories: Optional[list[Category]] = None
    ) -> list[PostId]:
        # TODO: this should probably not be in place store
        query = (
            sa.select(PostRow.id)
            .where(PostRow.place_id == place_id, ~PostRow.deleted)
            .where(PostRow.user_id.in_(user_ids))
        )
        if categories:
            query = query.where(PostRow.category.in_(categories))
        result = await self.db.execute(query)
        post_ids = result.scalars().all()
        return post_ids

    async def _create_place(self, name: str, latitude: float, longitude: float) -> Place:
        """Create a place in the database with the given details."""
        place = PlaceRow(name=name, latitude=latitude, longitude=longitude)
        self.db.add(place)
        await self.db.commit()
        await self.db.refresh(place)
        return Place.from_orm(place)
