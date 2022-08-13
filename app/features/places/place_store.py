from typing import Optional

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database.helpers import is_unique_column_error
from app.core.database.models import PlaceRow, PlaceDataRow
from app.core.types import UserId, PlaceId
from app.features.places.entities import Region, AdditionalPlaceData, Place
from app.features.places.place_query import PlaceQuery


class PlaceStore:
    def __init__(self, db: AsyncSession):
        self.db = db

    # Queries
    async def get_places(self, place_ids: set[PlaceId]) -> dict[PlaceId, Place]:
        places = await PlaceQuery().place_id_in(place_ids).execute_many(self.db)
        return {place.id: Place.from_orm(place) for place in places}

    async def get_place_name(self, place_id: PlaceId) -> Optional[str]:
        return await PlaceQuery(PlaceRow.name).place_id(place_id).execute_one(self.db)

    # Operations

    async def create_place(self, name: str, latitude: float, longitude: float) -> Place:
        """Create a place in the database with the given details."""
        place = PlaceRow(name=name, latitude=latitude, longitude=longitude)
        try:
            self.db.add(place)
            await self.db.commit()
            await self.db.refresh(place)
            return Place.from_orm(place)
        except IntegrityError as e:
            await self.db.rollback()
            if is_unique_column_error(e, PlaceRow.id.key):
                raise ValueError("UUID collision")
            # Otherwise, a place with the same (name, location) exists
            existing_place = await PlaceQuery().name(name).location(latitude, longitude).execute_one(self.db)
            if existing_place is None:
                raise ValueError("Failed to retrieve place.")
            return Place.from_orm(existing_place)

    async def get_place_by_id(self, place_id: PlaceId) -> Optional[Place]:
        place = await PlaceQuery().place_id(place_id).execute_one(self.db)
        return Place.from_orm(place) if place else None

    async def get_or_create_place(
        self,
        name: str,
        latitude: float,
        longitude: float,
        search_radius_meters: float = 10,
    ) -> Place:
        """Try to find an existing place matching the given request, otherwise create a place and return it."""
        place = await self.get_place(name, latitude, longitude, search_radius_meters)
        if place is not None:
            return place
        return await self.create_place(name, latitude, longitude)

    async def get_place(
        self,
        name: str,
        latitude: float,
        longitude: float,
        search_radius_meters: float = 10,
    ) -> Optional[Place]:
        """Try to find a place with the given name that is within the given region."""
        query = PlaceQuery().name(name).within_radius(latitude, longitude, search_radius_meters)
        place = await query.execute_one(self.db)
        return Place.from_orm(place) if place else None

    async def maybe_create_place_data(
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
