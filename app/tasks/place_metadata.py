import sqlalchemy as sa
from app.core.database.engine import get_db_context
from app.core.database.models import PlaceRow

from app.core.types import PlaceId

CITY_QUERY = """
select mode() within group (order by place_data.additional_data->'locality')
from place_data
where place_data.place_id = :place_id
"""

MKPOICATEGORY_QUERY = """
select mode() within group (order by place_data.additional_data->'poi_category')
from place_data
where place_data.place_id = :place_id
"""

# substr(..., 14) removes the leading 'MKPOICategory'
UPDATE_FOR_ALL_PLACES_QUERY = """
update place
set city = (
    select mode() within group (order by jsonb_object_field_text(place_data.additional_data, 'locality'))
    from place_data
    where place_data.place_id = place.id
), category = substr((
    select mode() within group (order by jsonb_object_field_text(place_data.additional_data, 'poi_category'))
    from place_data
    where place_data.place_id = place.id
), 14);
"""


async def update_place_metadata(place_id: PlaceId):
    """Update the place metadata based on the values in place_data."""
    async with get_db_context() as db:
        city = (await db.execute(sa.text(CITY_QUERY), {"place_id": place_id})).scalar_one_or_none()
        mapkit_category = (await db.execute(sa.text(MKPOICATEGORY_QUERY), {"place_id": place_id})).scalar_one_or_none()
        category = mapkit_category.removeprefix("MKPOICategory") if mapkit_category else None
        if city or category:
            await db.execute(sa.update(PlaceRow).where(PlaceRow.id == place_id).values(city=city, category=category))
            await db.commit()
