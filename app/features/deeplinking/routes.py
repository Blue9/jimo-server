import html
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse

from app.core.types import PostId

from app.features.posts.entities import InternalPost
from app.features.posts.post_store import PostStore
from app.features.stores import get_post_store, get_user_store
from app.features.users.user_store import UserStore

router = APIRouter()


@router.get("/post/{post_id}")
async def get_post_deeplink(
    post_id: PostId,
    post_store: PostStore = Depends(get_post_store),
    user_store: UserStore = Depends(get_user_store),
):
    # TODO: cache these three values
    username: str
    place_name: str
    image_url: str | None
    # endTODO
    post: InternalPost | None = await post_store.get_post(post_id=post_id)
    if post is None:
        raise HTTPException(404)
    user = await user_store.get_user(user_id=post.user_id)
    if user is None:
        raise HTTPException(404)
    username = user.username.lower()
    # It is possible for post.place.name to mess with the HTML so we need to escape it.
    place_name = html.escape(post.place.name)
    image_url = image_url = post.image_url or user.profile_picture_url
    title = html.escape(f"Check out {username}'s post about {place_name} on Jimo")
    deep_link = f"https://go.jimoapp.com/view-post?id={post_id}"
    preview_html = f"""
    <html>
        <head>
            <meta property="og:title" content="{title}">
            <meta property="og:image" content="{image_url}">
            <meta property="og:url" content="{deep_link}">
            <meta http-equiv="refresh" content="0; URL='{deep_link}'" />
        </head>
        <body>
            <a href="{deep_link}" rel="noopener noreferrer">
                <h1 style="font-family: sans-serif;">Loading {username}'s post. Tap here if you aren't automatically redirected.</h1>
            </a>
        </body>
    </html>
    """  # noqa
    return HTMLResponse(preview_html)


@router.get("/user/{username}")
async def get_user_deeplink(username: str, user_store: UserStore = Depends(get_user_store)):
    # TODO: cache these values
    username = username.lower()
    image_url: str | None
    # endTODO
    user = await user_store.get_user(username=username)
    if user is None:
        raise HTTPException(404)
    image_url = user.profile_picture_url
    title = f"Check out {username}'s profile on Jimo!"
    deep_link = f"https://go.jimoapp.com/view-profile?username={username}"
    preview_html = f"""
    <html>
        <head>
            <meta property="og:title" content="{title}">
            <meta property="og:image" content="{image_url}">
            <meta property="og:url" content="{deep_link}">
            <meta http-equiv="refresh" content="0; URL='{deep_link}'" />
        </head>
        <body>
            <a href="{deep_link}" rel="noopener noreferrer">
                <h1 style="font-family: sans-serif;">Loading {username}'s profile. Tap here if you aren't automatically redirected.</h1>
            </a>
        </body>
    </html>
    """  # noqa
    return HTMLResponse(preview_html)
