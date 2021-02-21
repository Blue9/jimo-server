from pydantic import validator

from app.schemas.base import Base


# Request types
class InviteUserRequest(Base):
    phone_number: str

    @validator("phone_number")
    def validate_phone_number(cls, phone_number):
        # TODO make sure it's in e164 format
        return phone_number


# Response types
class UserInviteStatus(Base):
    invited: bool


class UserWaitlistStatus(Base):
    invited: bool
    waitlisted: bool