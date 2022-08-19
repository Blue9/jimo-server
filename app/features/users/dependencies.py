from dataclasses import dataclass
from typing import Optional

from fastapi import Depends, HTTPException, Request

from app.core.firebase import FirebaseUser, get_firebase_user
from app.features.stores import get_user_store
from app.features.users.entities import InternalUser
from app.features.users.user_store import UserStore


@dataclass
class JimoUser:
    user: InternalUser


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
    user: Optional[InternalUser] = await user_store.get_user(uid=firebase_user.uid)
    if user is None or user.deleted:
        raise HTTPException(403)
    return JimoUser(user=user)


async def get_requested_user(username: str, user_store: UserStore = Depends(get_user_store)) -> JimoUser:
    user: Optional[InternalUser] = await user_store.get_user(username=username)
    if user is None or user.deleted:
        raise HTTPException(404)
    return JimoUser(user=user)
