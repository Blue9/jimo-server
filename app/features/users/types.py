from typing import Optional

from pydantic import validator
from shared.api import validators
from shared.api.base import Base, PhoneNumber
from shared.api.type_aliases import ImageId, CursorId
from shared.api.user import PublicUser, UserFieldErrors, UserRelation, NumMutualFriends


# Request types
class CreateUserRequest(Base):
    username: str
    first_name: str
    last_name: str

    _validate_username = validator("username", allow_reuse=True)(validators.validate_username)
    _validate_first_name = validator("first_name", allow_reuse=True)(validators.validate_name)
    _validate_last_name = validator("last_name", allow_reuse=True)(validators.validate_name)


class UpdateProfileRequest(Base):
    profile_picture_id: Optional[ImageId] = None
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None

    _validate_username = validator("username", allow_reuse=True)(validators.validate_username)
    _validate_first_name = validator("first_name", allow_reuse=True)(validators.validate_name)
    _validate_last_name = validator("last_name", allow_reuse=True)(validators.validate_name)


class PhoneNumberList(Base):
    phone_numbers: list[PhoneNumber]

    @validator("phone_numbers")
    def validate_phone_number(cls, phone_numbers):
        if len(phone_numbers) > 5000:
            raise ValueError("Phone number list too long, max length is 5000")
        return phone_numbers


class UsernameList(Base):
    usernames: list[str]

    @validator("usernames")
    def validate_usernames(cls, usernames):
        if len(usernames) > 100:
            raise ValueError("Username list too long, max length is 100")
        return usernames


# Response types
class CreateUserResponse(Base):
    created: Optional[PublicUser]
    error: Optional[UserFieldErrors]


class UpdateProfileResponse(Base):
    user: Optional[PublicUser]
    error: Optional[UserFieldErrors]


class FollowUserResponse(Base):
    followed: bool  # legacy, used for backwards compatibility
    followers: Optional[int]


class RelationToUser(Base):
    relation: Optional[UserRelation]


class FollowFeedItem(Base):
    user: PublicUser
    relation: Optional[UserRelation]


class SuggestedUserItem(Base):
    user: PublicUser
    num_mutual_friends: NumMutualFriends


class SuggestedUsersResponse(Base):
    users: list[SuggestedUserItem]


class FollowFeedResponse(Base):
    users: list[FollowFeedItem]
    cursor: Optional[CursorId]
