import re

from pydantic import BaseModel


def to_camel_case(snake_case: str) -> str:
    if not snake_case:
        return snake_case
    parts = snake_case.split('_')
    return parts[0] + "".join(part.title() for part in parts[1:])


class Base(BaseModel):
    class Config:
        orm_mode = True
        allow_population_by_field_name = True
        alias_generator = to_camel_case


class SimpleResponse(Base):
    success: bool


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
