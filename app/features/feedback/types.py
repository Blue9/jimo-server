from pydantic import field_validator

from app.core.types import Base


class FeedbackRequest(Base):
    contents: str
    follow_up: bool

    @field_validator("contents")
    @classmethod
    def validate_contents(cls, contents):
        if len(contents) == 0:
            raise ValueError("Feedback must be included")
        elif len(contents) > 2500:
            raise ValueError("Feedback too long")
        return contents
