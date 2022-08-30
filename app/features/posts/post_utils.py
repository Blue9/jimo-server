import uuid
from typing import Optional

from fastapi import HTTPException

from app.features.users.entities import InternalUser
from app.features.posts.entities import Post, InternalPost
from app.features.posts.post_store import PostStore
from app.features.users.relation_store import RelationStore
from app.features.users.user_store import UserStore


async def get_posts_from_post_ids(
    current_user: InternalUser,
    post_ids: list[uuid.UUID],
    post_store: PostStore,
    user_store: UserStore,
) -> list[Post]:
    # Step 1: Get internal posts
    internal_posts = await post_store.get_posts(post_ids)
    # Step 2: Get like and save statuses for each post
    liked_post_ids = await post_store.get_liked_posts(current_user.id, post_ids)
    saved_post_ids = await post_store.get_saved_posts(current_user.id, post_ids)
    # Step 3: Get users for each post
    user_ids = list(set(post.user_id for _, post in internal_posts.items()))
    users: dict[uuid.UUID, InternalUser] = await user_store.get_users(user_ids=user_ids)

    posts = []
    for post_id in post_ids:
        post = internal_posts.get(post_id)
        if post is None:
            continue
        place = post.place
        user = users.get(post.user_id)
        if user is None:
            continue
        public_post = Post(
            id=post_id,
            place=place,
            category=post.category,
            content=post.content,
            image_id=post.image_id,
            image_url=post.image_url,
            created_at=post.created_at,
            like_count=post.like_count,
            comment_count=post.comment_count,
            user=user,
            liked=post.id in liked_post_ids,
            saved=post.id in saved_post_ids,
        )
        posts.append(public_post)
    return posts


async def get_post_and_validate_or_raise(
    post_store: PostStore,
    relation_store: RelationStore,
    caller_user_id: uuid.UUID,
    post_id: uuid.UUID,
) -> InternalPost:
    """
    Check that the post exists and the given user is authorized to view it.

    Note: if the user is not authorized (the author blocked the caller user or has been blocked by the caller user),
    a 404 will be returned because they shouldn't even know that the post exists.
    """
    post: Optional[InternalPost] = await post_store.get_post(post_id)
    if post is None:
        raise HTTPException(404, detail="Post not found")
    if await relation_store.is_blocked(post.user_id, caller_user_id):
        raise HTTPException(404, detail="Post not found")
    if await relation_store.is_blocked(caller_user_id, post.user_id):
        raise HTTPException(404, detail="Post not found")
    return post