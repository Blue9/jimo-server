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
