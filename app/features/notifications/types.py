from typing import Optional

from pydantic import validator

from app.core.types import Base, CursorId
from app.features.notifications.entities import NotificationItem


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
