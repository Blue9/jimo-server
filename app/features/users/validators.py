import string
from typing import Optional


def validate_username(username: Optional[str]) -> str:
    if username is None:
        raise ValueError("Username missing")
    username = username.strip()
    if len(username) < 3 or len(username) > 20:
        raise ValueError("Username must be 3-20 characters")
    if any(c in username for c in string.whitespace):
        raise ValueError("Username can only contain letters, numbers, and underscores")
    if not username.replace("_", "").isalnum() or not username.isascii():
        raise ValueError("Username can only contain letters, numbers, and underscores")
    return username


def validate_name(name: Optional[str]) -> str:
    if name is None:
        raise ValueError("Name missing")
    name = name.strip()
    if len(name) < 1 or len(name) > 100:
        raise ValueError("Name must be 1-100 characters")
    return name
