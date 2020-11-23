from typing import Optional

from pydantic.main import BaseModel

from app.models.schemas import to_camel_case


class CreateUserRequest(BaseModel):
    uid: str
    email: str
    username: str
    first_name: str
    last_name: str

    class Config:
        alias_generator = to_camel_case


class UpdateUserRequest(BaseModel):
    username: Optional[str]
    first_name: Optional[str]
    last_name: Optional[str]
    private_account: Optional[bool]

    post_notifications: Optional[bool]
    follow_notifications: Optional[bool]
    post_liked_notifications: Optional[bool]

    class Config:
        alias_generator = to_camel_case
