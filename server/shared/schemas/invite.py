from typing import Optional

from shared.schemas.base import Base, PhoneNumber


# Request types
class InviteUserRequest(Base):
    phone_number: PhoneNumber


# Response types
class UserInviteStatus(Base):
    invited: bool
    message: Optional[str]


class UserWaitlistStatus(Base):
    invited: bool
    waitlisted: bool
