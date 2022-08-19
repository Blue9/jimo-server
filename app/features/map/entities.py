from typing import Optional

from app.features.places.entities import Location
from app.core.types import Base, PlaceId


class MapPinIcon(Base):
    category: Optional[str]  # Determines color of the pin
    icon_url: Optional[str]
    num_posts: int


class MapPin(Base):
    place_id: PlaceId
    location: Location
    icon: MapPinIcon
