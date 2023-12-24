from pydantic import field_validator

from app.core.types import Base, Category, UserId
from app.features.map.entities import MapPin, MapType
from app.features.places.entities import RectangularRegion


class GetMapRequest(Base):
    region: RectangularRegion
    map_type: MapType
    categories: list[Category] | None = None
    user_ids: list[UserId] | None = None
    min_stars: int | None = None

    @field_validator("min_stars")
    @classmethod
    def validate_min_stars(cls, min_stars):
        if min_stars is not None and (min_stars < 0 or min_stars > 3):
            raise ValueError("min_stars must be 1-3")
        return min_stars

    @field_validator("user_ids")
    @classmethod
    def validate_user_ids(cls, user_ids):
        if user_ids and len(user_ids) > 50:
            raise ValueError("User list too long, max length is 50")
        return user_ids


class GetMapResponse(Base):
    pins: list[MapPin]
