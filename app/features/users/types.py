from pydantic import field_validator

from app.core.types import Base, ImageId, PhoneNumber, CursorId
from app.features.users.entities import (
    PublicUser,
    UserFieldErrors,
    NumMutualFriends,
    UserRelation,
)
from app.features.users.primitive_types import ValidatedName, ValidatedUsername


class CreateUserRequest(Base):
    username: ValidatedUsername
    first_name: ValidatedName
    last_name: ValidatedName


class UpdateProfileRequest(Base):
    profile_picture_id: ImageId | None = None
    username: ValidatedUsername | None = None
    first_name: ValidatedName | None = None
    last_name: ValidatedName | None = None


class PhoneNumberList(Base):
    phone_numbers: list[PhoneNumber]

    @field_validator("phone_numbers")
    @classmethod
    def validate_phone_number(cls, phone_numbers):
        if len(phone_numbers) > 5000:
            raise ValueError("Phone number list too long, max length is 5000")
        return phone_numbers


class UsernameList(Base):
    usernames: list[str]

    @field_validator("usernames")
    @classmethod
    def validate_usernames(cls, usernames):
        if len(usernames) > 100:
            raise ValueError("Username list too long, max length is 100")
        return usernames


# Response types
class CreateUserResponse(Base):
    created: PublicUser | None
    error: UserFieldErrors | None


class UpdateProfileResponse(Base):
    user: PublicUser | None
    error: UserFieldErrors | None


class FollowUserResponse(Base):
    followed: bool  # legacy, used for backwards compatibility
    followers: int | None


class RelationToUser(Base):
    relation: UserRelation | None


class FollowFeedItem(Base):
    user: PublicUser
    relation: UserRelation | None


class SuggestedUserItem(Base):
    user: PublicUser
    num_mutual_friends: NumMutualFriends


class SuggestedUsersResponse(Base):
    users: list[SuggestedUserItem]


class FollowFeedResponse(Base):
    users: list[FollowFeedItem]
    cursor: CursorId | None
