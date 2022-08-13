from typing import Optional

from app.features.places.entities import Location
from app.core.types import Base, PlaceId


class MapPinIconV3(Base):
    category: Optional[str]  # Determines color of the pin
    icon_url: Optional[str]
    num_posts: int


class MapPinV3(Base):
    place_id: PlaceId
    location: Location
    icon: MapPinIconV3
