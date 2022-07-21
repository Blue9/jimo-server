from typing import Optional

from pydantic import validator
from shared.api.base import Base
from shared.api.notifications import NotificationItem
from shared.api.type_aliases import CursorId


class NotificationTokenRequest(Base):
    token: str

    @validator("token")
    def validate_token(cls, token):
        if len(token) == 0:
            raise ValueError("Invalid token")
        return token


class NotificationFeedResponse(Base):
    notifications: list[NotificationItem]
    cursor: Optional[CursorId]
