import re
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel

QueryEntity = Any


def to_camel_case(snake_case: str) -> str:
    if not snake_case:
        return snake_case
    parts = snake_case.split("_")
    return parts[0] + "".join(part.title() for part in parts[1:])


class InternalBase(BaseModel):
    class Config:
        orm_mode = True
        allow_population_by_field_name = True


class Base(InternalBase):
    class Config:
        alias_generator = to_camel_case


class PhoneNumber(str):
    """E.164 phone number validation (note: very lenient)."""

    regex = re.compile(r"^\+[1-9]\d{1,14}$")

    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not isinstance(v, str):
            raise TypeError("String required")
        m = cls.regex.fullmatch(v)
        if not m:
            raise ValueError("Invalid phone number format")
        return cls(f"{v}")

    def __repr__(self):
        return f"PhoneNumber({super().__repr__()})"


class Category(str, Enum):
    food = "food"
    activity = "activity"
    attraction = "attraction"
    lodging = "lodging"
    shopping = "shopping"
    nightlife = "nightlife"


class SimpleResponse(Base):
    success: bool


UserId = UUID
UserRelationId = UUID
PostLikeId = UUID
CommentLikeId = UUID
PostSaveId = UUID
PostId = UUID
PlaceId = UUID
PlaceDataId = UUID
CommentId = UUID
CursorId = UUID
ImageId = UUID
