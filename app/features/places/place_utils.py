from app.core.types import UserId, PlaceId
from app.features.places.place_store import PlaceStore
from app.features.posts.types import MaybeCreatePlaceRequest


async def get_or_create_place(
    user_id: UserId,
    request: MaybeCreatePlaceRequest,
    place_store: PlaceStore,
) -> PlaceId:
    loc = request.location
    radius = request.region.radius if request.region else 10
    place = await place_store.find_or_create_place(
        name=request.name,
        latitude=loc.latitude,
        longitude=loc.longitude,
        search_radius_meters=radius,
    )
    # Update place data
    region = request.region
    additional_data = request.additional_data
    await place_store.update_place_metadata(user_id, place.id, region, additional_data)
    return place.id
