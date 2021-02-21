import string


def is_valid_username(username: str) -> bool:
    if len(username) < 3 or len(username) > 20:
        return False
    if any(c in username for c in string.whitespace):
        return False
    if not username.replace("_", "").isalnum():
        return False
    return True


def is_valid_name(name: str) -> bool:
    name = name.strip()
    return 1 <= len(name) <= 100
