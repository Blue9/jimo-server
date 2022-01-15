import functools
import uuid
from asyncio import get_event_loop
from typing import Optional

from cachetools.func import lru_cache
from google.cloud import tasks_v2

from pydantic import BaseModel
from shared import schemas
from shared.schemas import internal

from app import config

client = tasks_v2.CloudTasksClient()


class CloudTasksConfig(BaseModel):
    project: str
    queue: str
    location: str
    url: str
    service_account_email: str


class BackgroundTaskHandler:
    def __init__(self, conf: CloudTasksConfig):
        self.project = conf.project
        self.queue = conf.queue
        self.location = conf.location
        self.url = conf.url
        self.service_account_email = conf.service_account_email
        self.queue_name = client.queue_path(self.project, self.location, self.queue)
        print("Initialized background task handler")

    async def _send_task(self, url_path: str, request: str):
        loop = get_event_loop()
        task = {
            "http_request": {
                "headers": {"Content-type": "application/json"},
                "body": request.encode(),
                "http_method": tasks_v2.HttpMethod.POST,
                "url": f"{self.url}/{url_path}",
                "oidc_token": {"service_account_email": self.service_account_email},
            }
        }
        return await loop.run_in_executor(
            None, functools.partial(client.create_task, request={"parent": self.queue_name, "task": task}))

    async def notify_post_liked(self, post: internal.InternalPost, place_name: str, liked_by: internal.InternalUser):
        path = "notifications/post/like"
        request = schemas.notifications.PostLikeNotification(post=post, place_name=place_name, liked_by=liked_by)
        return await self._send_task(path, request.json())

    async def notify_comment(
        self,
        post: internal.InternalPost,
        place_name: str,
        comment: str,
        comment_by: internal.InternalUser
    ):
        path = "notifications/comment"
        request = schemas.notifications.CommentNotification(post=post, place_name=place_name, comment=comment,
                                                            comment_by=comment_by)
        return await self._send_task(path, request.json())

    async def notify_comment_liked(self, comment: internal.InternalComment, liked_by: internal.InternalUser):
        path = "notifications/comment/like"
        request = schemas.notifications.CommentLikeNotification(comment=comment, liked_by=liked_by)
        return await self._send_task(path, request.json())

    async def notify_follow(self, user_id: uuid.UUID, followed_by: internal.InternalUser):
        path = "notifications/follow"
        request = schemas.notifications.FollowNotification(user_id=user_id, followed_by=followed_by)
        return await self._send_task(path, request.json())

    # Caching

    async def cache_objects(
        self,
        user_ids: Optional[list[uuid.UUID]] = None,
        post_ids: Optional[list[uuid.UUID]] = None,
        place_ids: Optional[list[uuid.UUID]] = None,
        comment_ids: Optional[list[uuid.UUID]] = None
    ):
        """Cache the given objects (if there are a lot of objects to cache split up into multiple calls)."""
        path = "cache/"
        request = schemas.caching.CacheRequest(
            user_ids=user_ids,
            post_ids=post_ids,
            place_ids=place_ids,
            comment_ids=comment_ids
        )
        return await self._send_task(path, request.json())

    async def delete_objects(
        self,
        user_ids: Optional[list[uuid.UUID]] = None,
        post_ids: Optional[list[uuid.UUID]] = None,
        place_ids: Optional[list[uuid.UUID]] = None,
        comment_ids: Optional[list[uuid.UUID]] = None
    ):
        """Delete the given objects (if there are a lot of objects to delete split up into multiple calls)."""
        path = "cache/delete"
        request = schemas.caching.CacheRequest(
            user_ids=user_ids,
            post_ids=post_ids,
            place_ids=place_ids,
            comment_ids=comment_ids
        )
        return await self._send_task(path, request.json())

    async def refresh_user_field(self, user_id: uuid.UUID, field: str):
        path = f"cache/users/field"
        request = schemas.caching.RefreshUserFieldRequest(id=user_id, field=field)
        return await self._send_task(path, request.json())

    async def cache_user_posts(self, user_id: uuid.UUID):
        path = f"cache/users/posts"
        request = schemas.caching.CacheListRequest(user_id=user_id)
        return await self._send_task(path, request.json())


@lru_cache(maxsize=1)
def get_task_handler() -> Optional[BackgroundTaskHandler]:
    if config.CLOUD_TASKS_CONFIG is not None:
        return BackgroundTaskHandler(config.CLOUD_TASKS_CONFIG)
    return None
