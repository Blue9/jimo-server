from datetime import datetime
from functools import cached_property
from uuid import UUID

from pydantic import Field, computed_field, field_validator

from app.core.types import Base, PlaceId


class Location(Base):
    latitude: float
    longitude: float

    @field_validator("latitude")
    @classmethod
    def validate_latitude(cls, latitude):
        if latitude < -90 or latitude > 90:
            raise ValueError("Invalid latitude")
        return latitude

    @field_validator("longitude")
    @classmethod
    def validate_longitude(cls, longitude):
        if longitude < -180 or longitude > 180:
            raise ValueError("Invalid longitude")
        return longitude


class RectangularRegion(Base):
    x_min: float
    y_min: float
    x_max: float
    y_max: float

    @field_validator("x_min")
    @classmethod
    def validate_x_min(cls, x_min):
        if x_min < -180 or x_min > 180:
            raise ValueError("Invalid min longitude")
        return x_min

    @field_validator("y_min")
    @classmethod
    def validate_y_min(cls, y_min):
        if y_min < -90 or y_min > 90:
            raise ValueError("Invalid min latitude")
        return y_min

    @field_validator("x_max")
    @classmethod
    def validate_x_max(cls, x_max):
        if x_max < -180 or x_max > 180:
            raise ValueError("Invalid max longitude")
        return x_max

    @field_validator("y_max")
    @classmethod
    def validate_y_max(cls, y_max):
        if y_max < -90 or y_max > 90:
            raise ValueError("Invalid max latitude")
        return y_max


class Region(Location):
    radius: float

    @field_validator("radius")
    @classmethod
    def validate_radius(cls, radius):
        if radius < 0 or radius > 20e6:
            # Russia is about 9,000 km wide, so 10,000 km is a fair upper bound
            raise ValueError("Invalid radius")
        return radius


class Place(Base):
    id: PlaceId = Field(serialization_alias="placeId")
    name: str
    city: str | None
    regionName: str | None = None  # DEPRECATED
    category: str | None
    latitude: float
    longitude: float

    @computed_field
    @cached_property
    def location(self) -> Location:
        return Location(latitude=self.latitude, longitude=self.longitude)


class SavedPlace(Base):
    id: UUID
    place: Place
    note: str
    created_at: datetime

    @field_validator("created_at")
    @classmethod
    def validate_created_at(cls, created_at):
        # Needed so Swift can automatically decode
        return created_at.replace(microsecond=0)

    @field_validator("note")
    @classmethod
    def validate_content(cls, note):
        note = note.strip()
        if len(note) > 2000:
            raise ValueError("Note too long (max length 2000 chars)")
        return note


class AdditionalPlaceData(Base):
    country_code: str | None = None
    country: str | None = None
    postal_code: str | None = None
    administrative_area: str | None = None
    sub_administrative_area: str | None = None
    locality: str | None = None
    sub_locality: str | None = None
    thoroughfare: str | None = None
    sub_thoroughfare: str | None = None
    poi_category: str | None = None
    phone_number: str | None = None
    url: str | None = None
    time_zone: str | None = None
