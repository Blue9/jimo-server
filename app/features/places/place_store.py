from typing import Optional

import sqlalchemy as sa
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.core.database.models import (
    PlaceRow,
    PlaceDataRow,
    PlaceSaveRow,
    PostRow,
    UserRelationRow,
    UserRelationType,
    UserRow,
)
from app.core.types import UserId, PlaceId, PostId, Category
from app.features.places.entities import Region, AdditionalPlaceData, Place
from app.features.places.types import SavedPlace


class PlaceStore:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_place(self, place_id: PlaceId) -> Optional[Place]:
        query = sa.select(PlaceRow).where(PlaceRow.id == place_id)
        result = await self.db.execute(query)
        place_row = result.scalars().first()
        return Place.model_validate(place_row) if place_row else None

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
        return Place.model_validate(maybe_place) if maybe_place else None

    async def get_place_save(self, user_id: UserId, place_id: PlaceId) -> SavedPlace | None:
        result = await self.db.execute(
            sa.select(PlaceSaveRow)
            .options(joinedload(PlaceSaveRow.place))
            .where(PlaceSaveRow.user_id == user_id, PlaceSaveRow.place_id == place_id)
        )
        maybe_place_save = result.scalars().first()
        return SavedPlace.model_validate(maybe_place_save) if maybe_place_save else None

    async def save_place(
        self, user_id: UserId, place_id: PlaceId, note: str, category: str | None = None
    ) -> SavedPlace:
        place_save = PlaceSaveRow(user_id=user_id, place_id=place_id, note=note, category=category)
        self.db.add(place_save)
        try:
            await self.db.commit()
        except IntegrityError:
            # Already saved place, update note
            await self.db.rollback()
            await self.db.execute(
                sa.update(PlaceSaveRow)
                .where(PlaceSaveRow.user_id == user_id, PlaceSaveRow.place_id == place_id)
                .values(note=note)
            )
            await self.db.commit()
        created_save = await self.get_place_save(user_id=user_id, place_id=place_id)
        if created_save is None:
            raise ValueError("Could not save place")
        return created_save

    async def unsave_place(self, user_id: UserId, place_id: PlaceId) -> None:
        query = sa.delete(PlaceSaveRow).where(PlaceSaveRow.user_id == user_id, PlaceSaveRow.place_id == place_id)
        await self.db.execute(query)
        await self.db.commit()

    async def get_saved_places(
        self, user_id: UserId, cursor: PlaceId | None = None, limit: int = 15
    ) -> list[SavedPlace]:
        query = (
            sa.select(PlaceSaveRow.id, PlaceRow, PlaceSaveRow.note, PlaceSaveRow.created_at)
            .select_from(PlaceSaveRow)
            .join(PlaceRow)
            .where(PlaceSaveRow.user_id == user_id)
        )
        if cursor:
            query = query.where(PlaceSaveRow.id < cursor)
        query = query.order_by(PlaceSaveRow.id.desc()).limit(limit)
        result = await self.db.execute(query)
        saves = result.all()
        return [
            SavedPlace(id=id, place=place, note=note, created_at=created_at) for id, place, note, created_at in saves
        ]

    async def get_saved_place_ids(self, user_id: UserId, place_ids: list[PlaceId]) -> set[PlaceId]:
        query = (
            sa.select(PlaceSaveRow.place_id)
            .select_from(PlaceSaveRow)
            .where(PlaceSaveRow.user_id == user_id, PlaceSaveRow.place_id.in_(place_ids))
        )
        result = await self.db.execute(query)
        saved_places: list[PlaceId] = result.scalars().all()  # type: ignore
        return set(saved_places)

    async def is_place_saved(self, user_id: UserId, place_id: PlaceId) -> bool:
        """Return whether the given place is saved by the given user."""
        query = sa.select(PlaceSaveRow.id).where(PlaceSaveRow.place_id == place_id, PlaceSaveRow.user_id == user_id)
        result = await self.db.execute(query.exists().select())
        is_saved: bool = result.scalar()  # type: ignore
        return is_saved

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
            place_data.additional_data = additional_data.model_dump()
        try:
            self.db.add(place_data)
            await self.db.commit()
        except IntegrityError:
            await self.db.rollback()

    async def get_community_posts(self, place_id: PlaceId, categories: Optional[list[Category]] = None) -> list[PostId]:
        query = (
            sa.select(PostRow.id)
            .where(PostRow.place_id == place_id, ~PostRow.deleted)
            .where(PostRow.image_id.is_not(None) | (PostRow.content != ""))
        )
        if categories:
            query = query.where(PostRow.category.in_(categories))
        result = await self.db.execute(query.order_by(PostRow.id.desc()))
        post_ids: list[PostId] = result.scalars().all()  # type: ignore
        return post_ids

    async def get_featured_user_posts(self, place_id: PlaceId) -> list[PostId]:
        query = (
            sa.select(PostRow.id)
            .join(UserRow, UserRow.id == PostRow.user_id)
            .where(UserRow.is_featured)
            .where(PostRow.place_id == place_id, ~PostRow.deleted)
        )
        result = await self.db.execute(query.order_by(PostRow.id.desc()))
        post_ids: list[PostId] = result.scalars().all()  # type: ignore
        return post_ids

    async def get_friend_posts(
        self, place_id: PlaceId, user_id: UserId, categories: Optional[list[Category]] = None
    ) -> list[PostId]:
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
        result = await self.db.execute(query.order_by(PostRow.id.desc()))
        post_ids: list[PostId] = result.scalars().all()  # type: ignore
        return post_ids

    async def _create_place(self, name: str, latitude: float, longitude: float) -> Place:
        """Create a place in the database with the given details."""
        place = PlaceRow(name=name, latitude=latitude, longitude=longitude)
        self.db.add(place)
        await self.db.commit()
        await self.db.refresh(place)
        return Place.model_validate(place)
