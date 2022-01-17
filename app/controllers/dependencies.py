from dataclasses import dataclass
from functools import lru_cache
from typing import Optional

import aioredis
from fastapi import Depends, HTTPException, Request
from shared import schemas
from shared.caching.lists import UserPostsCache
from shared.caching.users import UserCache
from shared.stores.post_store import PostStore
from shared.stores.user_store import UserStore

from app.api.utils import get_user_store, get_post_store

from app.config import REDIS_URL
from app.controllers.firebase import FirebaseUser, get_firebase_user
from app.controllers.tasks import BackgroundTaskHandler, get_task_handler


@dataclass
class WrappedUser:
    user: schemas.internal.InternalUser
    is_cached: bool


@lru_cache(maxsize=1)
def get_redis():
    return aioredis.from_url(REDIS_URL, decode_responses=True)


def get_authorization_header(request: Request) -> str:
    """Used for rate limiting."""
    authorization = request.headers.get("authorization")
    if authorization is None or not authorization.startswith("Bearer "):
        return "default"
    return authorization[7:]


async def get_user_cache(user_store: UserStore = Depends(get_user_store)):
    return UserCache(redis=get_redis(), user_store=user_store)


async def get_user_posts_cache(post_store: PostStore = Depends(get_post_store)):
    return UserPostsCache(redis=get_redis(), post_store=post_store)


async def get_caller_user(
    firebase_user: FirebaseUser = Depends(get_firebase_user),
    user_store: UserStore = Depends(get_user_store),
    user_cache: UserCache = Depends(get_user_cache),
    task_handler: Optional[BackgroundTaskHandler] = Depends(get_task_handler)
) -> WrappedUser:
    is_cached = True
    user: Optional[schemas.internal.InternalUser] = await user_cache.get_user_by_uid(firebase_user.uid)
    if user is None:
        is_cached = False
        user = await user_store.get_user_by_uid(firebase_user.uid)
    if user is None or user.deleted:
        raise HTTPException(403)
    if task_handler is not None and not is_cached:
        await task_handler.cache_objects(user_ids=[user.id])
    return WrappedUser(user=user, is_cached=is_cached)


async def get_requested_user(
    username: str,
    user_store: UserStore = Depends(get_user_store),
    user_cache: UserCache = Depends(get_user_cache),
    task_handler: Optional[BackgroundTaskHandler] = Depends(get_task_handler)
) -> WrappedUser:
    is_cached = True
    user: Optional[schemas.internal.InternalUser] = await user_cache.get_user_by_username(username)
    if user is None:
        is_cached = False
        user = await user_store.get_user_by_username(username)
    if user is None or user.deleted:
        raise HTTPException(404)
    if task_handler is not None and not is_cached:
        await task_handler.cache_objects(user_ids=[user.id])
    return WrappedUser(user=user, is_cached=is_cached)
