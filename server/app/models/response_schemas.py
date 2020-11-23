from typing import Optional, Dict

from pydantic.main import BaseModel

from app.models.schemas import PrivateUser, to_camel_case


class CreateUserResponse(BaseModel):
    created: bool


class UpdateUserErrors(BaseModel):
    username: Optional[str]
    first_name: Optional[str]
    last_name: Optional[str]
    private_account: Optional[str]
    post_notifications: Optional[str]
    follow_notifications: Optional[str]
    post_liked_notifications: Optional[str]

    class Config:
        allow_population_by_field_name = True
        alias_generator = to_camel_case


class UpdateUserResponse(BaseModel):
    user: Optional[PrivateUser]
    errors: Optional[UpdateUserErrors]
