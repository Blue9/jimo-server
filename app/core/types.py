import re
from enum import Enum
from typing import Annotated, Any, TypeAliasType
from uuid import UUID

from pydantic import AfterValidator, BaseModel

QueryEntity = Any


def to_camel_case(snake_case: str) -> str:
    if not snake_case:
        return snake_case
    parts = snake_case.split("_")
    return parts[0] + "".join(part.title() for part in parts[1:])


class InternalBase(BaseModel):
    model_config = {
        "from_attributes": True,
        "populate_by_name": True,
    }


class Base(BaseModel):
    model_config = {
        "from_attributes": True,
        "populate_by_name": True,
        "alias_generator": to_camel_case,
        "validate_default": True,
    }


class PhoneNumberValidator:
    """E.164 phone number validation (note: very lenient)."""

    regex = re.compile(r"^\+[1-9]\d{1,14}$")

    @classmethod
    def validate(cls, v):
        if not isinstance(v, str):
            raise TypeError("String required")
        m = cls.regex.fullmatch(v)
        if not m:
            raise ValueError("Invalid phone number format")
        return v


PhoneNumber = TypeAliasType("PhoneNumber", Annotated[str, AfterValidator(PhoneNumberValidator.validate)])


class Category(str, Enum):
    food = "food"
    cafe = "cafe"
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
