"""Database defaults."""
import uuid

import ulid


def gen_ulid() -> uuid.UUID:
    """
    Generate a ULID.

    More info here: https://github.com/ulid/spec. Basic idea is that they are 48 bits timestamp + 80 bits randomness,
    better than uuid v4 since we don't need to sort by created_at and better than bigint since they aren't easily
    guessable.
    """
    return ulid.new().uuid
