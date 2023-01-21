from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import Field, validator, root_validator

from app.core.types import Base, PlaceId


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


class RectangularRegion(Base):
    x_min: float
    y_min: float
    x_max: float
    y_max: float

    @validator("x_min")
    def validate_x_min(cls, x_min):
        if x_min < -180 or x_min > 180:
            raise ValueError("Invalid min longitude")
        return x_min

    @validator("y_min")
    def validate_y_min(cls, y_min):
        if y_min < -90 or y_min > 90:
            raise ValueError("Invalid min latitude")
        return y_min

    @validator("x_max")
    def validate_x_max(cls, x_max):
        if x_max < -180 or x_max > 180:
            raise ValueError("Invalid max longitude")
        return x_max

    @validator("y_max")
    def validate_y_max(cls, y_max):
        if y_max < -90 or y_max > 90:
            raise ValueError("Invalid max latitude")
        return y_max


class Region(Location):
    radius: float

    @validator("radius")
    def validate_radius(cls, radius):
        if radius < 0 or radius > 20e6:
            # Russia is about 9,000 km wide, so 10,000 km is a fair upper bound
            raise ValueError("Invalid radius")
        return radius


class Place(Base):
    id: PlaceId = Field(alias="placeId")
    name: str
    region_name: Optional[str]
    location: Location

    @root_validator(pre=True)
    def get_location(cls, values):
        if values.get("latitude") is not None and values.get("longitude") is not None:
            return dict(
                values,
                location=Location(latitude=values["latitude"], longitude=values["longitude"]),
            )
        return values


class SavedPlace(Base):
    id: UUID
    place: Place
    note: str
    created_at: datetime

    @validator("created_at")
    def validate_created_at(cls, created_at):
        # Needed so Swift can automatically decode
        return created_at.replace(microsecond=0)

    @validator("note")
    def validate_content(cls, note):
        note = note.strip()
        if len(note) > 2000:
            raise ValueError("Note too long (max length 2000 chars)")
        return note


class AdditionalPlaceData(Base):
    country_code: Optional[str]
    country: Optional[str]
    postal_code: Optional[str]
    administrative_area: Optional[str]
    sub_administrative_area: Optional[str]
    locality: Optional[str]
    sub_locality: Optional[str]
    thoroughfare: Optional[str]
    sub_thoroughfare: Optional[str]
    poi_category: Optional[str]
    phone_number: Optional[str]
    url: Optional[str]
    time_zone: Optional[str]
