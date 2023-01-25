import httpx

from app.core import config
from app.features.places.entities import SavedPlace
from app.features.posts.entities import InternalPost
from app.utils import get_logger

log = get_logger(__name__)


async def slack_post_created(username: str, post: InternalPost):
    """Send a message that a user created a post."""
    deep_link = f"https://go.jimoapp.com/view-post?id={str(post.id)}"
    message = f"{username} just posted about {post.place.name} in {post.place.region_name}. View more: {deep_link}"
    await _send_message(message)


async def slack_place_saved(username: str, save: SavedPlace):
    """Send a message that a user saved a place."""
    message = f"{username} just saved {save.place.name} (note length: {len(save.note)})"
    await _send_message(message)


async def _send_message(message: str):
    if not config.SLACK_HOOK:
        return
    web_hook = config.SLACK_HOOK
    if not web_hook.startswith("https://hooks.slack.com/"):
        log.warn("Invalid web hook URL")
        return
    async with httpx.AsyncClient() as client:
        response = await client.post(web_hook, json=dict(text=message))
        if response.status_code != 200:
            log.warn("Failed to send Slack message")
