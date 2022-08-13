from typing import Optional

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
