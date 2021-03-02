import uuid
from typing import Optional

from pydantic import Field, validator, root_validator

from app.schemas.base import Base


# ORM types
class Location(Base):
    latitude: float
    longitude: float

    @validator("latitude")
    def validate_latitude(cls, latitude):
        if latitude < -90 or latitude > 90:
            raise ValueError("Invalid latitude")
        return latitude

    @validator("longitude")
    def validate_longitude(cls, longitude):
        if longitude < -180 or longitude > 180:
            raise ValueError("Invalid longitude")
        return longitude


class Region(Location):
    radius: float

    @validator("radius")
    def validate_radius(cls, radius):
        if radius < 0 or radius > 10e6:
            # Russia is about 9,000 km wide, so 10,000 km is a fair upper bound
            raise ValueError("Invalid radius")
        return radius


class Place(Base):
    urlsafe_id: uuid.UUID = Field(alias="placeId")
    name: str
    location: Location

    @root_validator(pre=True)
    def get_location(cls, values):
        if values.get("latitude") is not None and values.get("longitude") is not None:
            return dict(values, location=Location(latitude=values["latitude"], longitude=values["longitude"]))
        return values


# Request types
class MaybeCreatePlaceRequest(Base):
    name: str
    location: Location
    region: Optional[Region]

    @validator("name")
    def validate_name(cls, name):
        name = name.strip()
        if len(name) == 0 or len(name) > 1000:
            raise ValueError("Invalid name")
        return name


class RectangularRegion(Base):
    center_lat: float
    center_long: float
    span_lat: float
    span_long: float

    @root_validator(pre=True)
    def get_region(cls, values):
        assert -90 <= values.get("center_lat") <= 90
        assert -180 <= values.get("center_long") <= 180
        assert 0 <= values.get("span_lat") <= 180
        assert 0 <= values.get("span_long") <= 360
        return values
