from typing import Literal

from app.features.places.entities import Location
from app.core.types import Base, PlaceId


class MapPinIcon(Base):
    category: str | None  # Determines color of the pin
    icon_url: str | None
    num_posts: int


class MapPin(Base):
    place_id: PlaceId
    location: Location
    icon: MapPinIcon


MapType = Literal["community", "following", "saved", "custom", "me"]
