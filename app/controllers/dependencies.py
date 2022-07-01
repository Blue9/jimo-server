from dataclasses import dataclass
from functools import lru_cache
from typing import Optional

import aioredis
from fastapi import Depends, HTTPException, Request
from shared.api.internal import InternalUser
from shared.stores.user_store import UserStore

from app.api.utils import get_user_store
from app.config import REDIS_URL
from app.controllers.firebase import FirebaseUser, get_firebase_user


@dataclass
class JimoUser:
    user: InternalUser


@lru_cache(maxsize=1)
def get_redis():
    return aioredis.from_url(REDIS_URL, decode_responses=True)


def get_authorization_header(request: Request) -> str:
    """Used for rate limiting."""
    authorization = request.headers.get("authorization")
    if authorization is None or not authorization.startswith("Bearer "):
        return "default"
    return authorization[7:]


async def get_caller_user(
    firebase_user: FirebaseUser = Depends(get_firebase_user),
    user_store: UserStore = Depends(get_user_store),
) -> JimoUser:
    user: Optional[InternalUser] = await user_store.get_user_by_uid(firebase_user.uid)
    if user is None or user.deleted:
        raise HTTPException(403)
    return JimoUser(user=user)


async def get_requested_user(username: str, user_store: UserStore = Depends(get_user_store)) -> JimoUser:
    user: Optional[InternalUser] = await user_store.get_user_by_username(username)
    if user is None or user.deleted:
        raise HTTPException(404)
    return JimoUser(user=user)
