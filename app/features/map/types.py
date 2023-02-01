from pydantic import validator

from app.core.types import Base, Category, UserId
from app.features.map.entities import MapPin, MapType
from app.features.places.entities import RectangularRegion


class GetMapRequest(Base):
    region: RectangularRegion
    map_type: MapType
    categories: list[Category] | None
    user_ids: list[UserId] | None

    @validator("user_ids")
    def validate_user_ids(cls, user_ids):
        if user_ids and len(user_ids) > 100:
            raise ValueError("User list too long, max length is 100")
        return user_ids


class GetMapResponse(Base):
    pins: list[MapPin]
