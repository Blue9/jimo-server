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
from app.utils import get_logger

client = tasks_v2.CloudTasksClient()
log = get_logger(__name__)


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
        log.info("Initialized background task handler")

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

    async def notify_post_saved(self, post: internal.InternalPost, place_name: str, saved_by: internal.InternalUser):
        path = "notifications/post/save"
        request = schemas.notifications.PostSaveNotification(post=post, place_name=place_name, saved_by=saved_by)
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


@lru_cache(maxsize=1)
def get_task_handler() -> Optional[BackgroundTaskHandler]:
    if config.CLOUD_TASKS_CONFIG is not None:
        return BackgroundTaskHandler(config.CLOUD_TASKS_CONFIG)
    return None
