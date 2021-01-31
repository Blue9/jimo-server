from typing import Optional

from app.models.schemas import Base, PrivateUser


class UserFieldErrors(Base):
    uid: Optional[str]
    username: Optional[str]
    first_name: Optional[str]
    last_name: Optional[str]
    private_account: Optional[str]
    post_notifications: Optional[str]
    follow_notifications: Optional[str]
    post_liked_notifications: Optional[str]


class CreateUserResponse(Base):
    created: Optional[PrivateUser]
    error: Optional[UserFieldErrors]


class UpdateUserResponse(Base):
    user: Optional[PrivateUser]
    errors: Optional[UserFieldErrors]


class LikePostResponse(Base):
    likes: int


class DeletePostResponse(Base):
    deleted: bool
