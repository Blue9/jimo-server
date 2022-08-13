import typing

import sqlalchemy as sa
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database.models import PlaceRow
from app.core.types import PlaceId, QueryEntity

PlaceQueryT = typing.TypeVar("PlaceQueryT", bound="PlaceQuery")


class PlaceQuery:
    def __init__(self, query_entity: QueryEntity = PlaceRow):
        self.query = sa.select(query_entity)

    def place_id(self: PlaceQueryT, place_id: PlaceId) -> PlaceQueryT:
        self.query = self.query.where(PlaceRow.id == place_id)
        return self

    def name(self: PlaceQueryT, name: str) -> PlaceQueryT:
        self.query = self.query.where(PlaceRow.name == name)
        return self

    def location(self: PlaceQueryT, latitude: float, longitude: float) -> PlaceQueryT:
        self.query = self.query.where(PlaceRow.latitude == latitude, PlaceRow.longitude == longitude)
        return self

    def place_id_in(self: PlaceQueryT, place_ids: typing.Collection[PlaceId]) -> PlaceQueryT:
        self.query = self.query.where(PlaceRow.id.in_(place_ids))
        return self

    def within_radius(self: PlaceQueryT, latitude: float, longitude: float, radius_meters: float) -> PlaceQueryT:
        point = func.ST_GeographyFromText(f"POINT({longitude} {latitude})")
        self.query = self.query.where(func.ST_Distance(point, PlaceRow.location) <= radius_meters)
        return self

    async def execute_many(self: PlaceQueryT, session: AsyncSession) -> list[QueryEntity]:
        result = await session.execute(self.query)
        return result.scalars().all()

    async def execute_one(self: PlaceQueryT, session: AsyncSession) -> typing.Optional[QueryEntity]:
        result = await session.execute(self.query)
        return result.scalars().first()
