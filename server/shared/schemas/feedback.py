from pydantic import validator

from shared.schemas.base import Base


class FeedbackRequest(Base):
    contents: str
    follow_up: bool

    @validator("contents")
    def validate_contents(cls, contents):
        if len(contents) == 0:
            raise ValueError("Feedback must be included")
        elif len(contents) > 2500:
            raise ValueError("Feedback too long")
        return contents
