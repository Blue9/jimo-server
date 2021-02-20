from typing import Optional

from app.models.schemas import Base, PrivateUser


class UserFieldErrors(Base):
    uid: Optional[str]
    username: Optional[str]
    first_name: Optional[str]
    last_name: Optional[str]
    other: Optional[str]


class CreateUserResponse(Base):
    created: Optional[PrivateUser]
    error: Optional[UserFieldErrors]


class UpdateProfileResponse(Base):
    user: Optional[PrivateUser]
    error: Optional[UserFieldErrors]


class LikePostResponse(Base):
    likes: int


class DeletePostResponse(Base):
    deleted: bool


class FollowUserResponse(Base):
    followed: bool
    followers: Optional[int]


class UserInviteStatus(Base):
    invited: bool


class UserWaitlistStatus(Base):
    invited: bool
    waitlisted: bool


class SimpleResponse(Base):
    success: bool
