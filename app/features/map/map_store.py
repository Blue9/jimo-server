from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.map.entities import MapPinV3, MapPinIconV3
from app.features.places.entities import Location, Region
from app.core.types import PlaceId
from app.features.map.filters import MapFilter, CategoryFilter
from app.core.database.complex_queries import map_v3_query


class MapStore:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_map_v3(
        self,
        region: Region,
        map_filter: MapFilter,
        category_filter: CategoryFilter,
        limit: int = 500,
    ) -> list[MapPinV3]:
        query = map_v3_query(region, map_filter, category_filter, limit)
        rows = (await self.db.execute(query)).all()
        pins = []
        pin_icons = dict()
        # TODO: clean up
        for row in rows:
            place_id: PlaceId = row[0]
            category: str = row[3]
            profile_picture_url: Optional[str] = row[4]
            if place_id not in pin_icons:
                pin_icons[place_id] = MapPinIconV3(category=category, icon_url=profile_picture_url, num_posts=1)
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
                MapPinV3(
                    place_id=place_id,
                    location=Location(latitude=latitude, longitude=longitude),
                    icon=pin_icons[place_id],
                )
            )
        return pins
