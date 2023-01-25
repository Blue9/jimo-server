from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.core.database.helpers import (
    eager_load_user_options,
    eager_load_post_options,
    is_comment_liked_query,
    eager_load_comment_options,
)
from app.core.database.models import (
    CommentRow,
    PostRow,
    PostLikeRow,
    UserRow,
    UserRelationRow,
    UserRelationType,
)
from app.core.types import UserId, PostId, CursorId
from app.features.comments.entities import CommentWithoutLikeStatus
from app.features.comments.types import Comment
from app.features.notifications.types import ItemType, NotificationItem
from app.features.places.place_store import PlaceStore
from app.features.posts.entities import PostWithoutLikeSaveStatus, Post
from app.features.posts.post_store import PostStore


class ActivityFeedStore:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_notification_feed(
        self,
        post_store: PostStore,
        place_store: PlaceStore,
        user_id: UserId,
        cursor: Optional[CursorId] = None,
        limit: int = 50,
    ) -> tuple[list[NotificationItem], Optional[CursorId]]:
        follow_feed = await self.get_follow_feed(user_id, cursor, limit)
        post_like_feed = await self.get_post_like_feed(post_store, place_store, user_id, cursor, limit)
        comment_feed = await self.get_comment_feed(post_store, place_store, user_id, cursor, limit)
        merged = follow_feed + post_like_feed + comment_feed
        items = sorted(merged, key=lambda i: i.item_id, reverse=True)[:limit]
        next_cursor = items[-1].item_id if len(items) >= limit else None
        return items, next_cursor

    async def get_follow_feed(
        self, user_id: UserId, cursor: Optional[CursorId] = None, limit: int = 50
    ) -> list[NotificationItem]:
        follow_query = (
            select(UserRelationRow, UserRow)
            .options(*eager_load_user_options())
            .where(
                UserRelationRow.to_user_id == user_id,
                UserRow.id == UserRelationRow.from_user_id,
                UserRelationRow.relation == UserRelationType.following,
                ~UserRow.deleted,
            )
        )
        if cursor is not None:
            follow_query = follow_query.where(UserRelationRow.id < cursor)
        result = await self.db.execute(follow_query.order_by(UserRelationRow.id.desc()).limit(limit))
        follow_results = result.all()
        follow_items = []
        for f in follow_results:
            follow_items.append(
                NotificationItem(
                    type=ItemType.follow,
                    created_at=f.UserRelationRow.created_at,
                    user=f.UserRow,
                    item_id=f.UserRelationRow.id,
                )
            )
        return follow_items

    async def get_post_like_feed(
        self,
        post_store: PostStore,
        place_store: PlaceStore,
        user_id: UserId,
        cursor: Optional[CursorId] = None,
        limit: int = 50,
    ) -> list[NotificationItem]:
        like_query = (
            select(PostLikeRow, PostRow)
            .options(joinedload(PostLikeRow.liked_by).options(*eager_load_user_options()), *eager_load_post_options())
            .where(
                PostLikeRow.post_id == PostRow.id,
                PostRow.user_id == user_id,
                ~PostRow.deleted,
                PostLikeRow.user_id != user_id,
                PostLikeRow.liked_by.has(deleted=False),
            )
        )
        if cursor is not None:
            like_query = like_query.where(PostLikeRow.id < cursor)

        result = await self.db.execute(like_query.order_by(PostLikeRow.id.desc()).limit(limit))
        like_results = result.all()
        post_ids = [post.id for _, post in like_results]
        place_ids = [post.place.id for _, post in like_results]
        liked_posts = await post_store.get_liked_posts(user_id, post_ids)

        saved_place_ids = await place_store.get_saved_place_ids(user_id=user_id, place_ids=place_ids)
        like_items = []
        for post_like, post in like_results:
            fields = PostWithoutLikeSaveStatus.from_orm(post).dict()
            external_post = Post(**fields, liked=post.id in liked_posts, saved=post.place.id in saved_place_ids)
            like_items.append(
                NotificationItem(
                    type=ItemType.like,
                    created_at=post_like.created_at,
                    user=post_like.liked_by,
                    item_id=post_like.id,
                    post=external_post,
                )
            )
        return like_items

    async def get_comment_feed(
        self,
        post_store: PostStore,
        place_store: PlaceStore,
        user_id: UserId,
        cursor: Optional[CursorId] = None,
        limit: int = 50,
    ) -> list[NotificationItem]:
        comment_query = (
            select(CommentRow, is_comment_liked_query(user_id))
            .options(*eager_load_comment_options())
            .join(PostRow)
            .where(
                CommentRow.post_id == PostRow.id,
                PostRow.user_id == user_id,
                CommentRow.user_id != user_id,
                ~CommentRow.deleted,
                ~PostRow.deleted,
                CommentRow.user.has(deleted=False),
            )
        )
        if cursor:
            comment_query = comment_query.where(CommentRow.id < cursor)
        result = await self.db.execute(comment_query.order_by(CommentRow.id.desc()).limit(limit))
        comment_rows = result.all()
        post_ids = [row.CommentRow.post_id for row in comment_rows]
        comment_items = []
        posts = await self._get_db_posts(post_ids)
        place_ids = [post.place.id for post in posts]
        posts_by_id = {post.id: post for post in posts}
        liked_posts = await post_store.get_liked_posts(user_id, post_ids)
        saved_place_ids = await place_store.get_saved_place_ids(user_id=user_id, place_ids=place_ids)
        for row in comment_rows:
            comment: CommentRow = row.CommentRow
            post: Optional[PostRow] = posts_by_id.get(comment.post_id)
            if post is None:  # Should never happen but just in case
                continue
            is_post_liked = post.id in liked_posts
            is_post_saved = post.place.id in saved_place_ids
            is_comment_liked: bool = row.comment_liked
            external_post = Post(
                **PostWithoutLikeSaveStatus.from_orm(post).dict(), liked=is_post_liked, saved=is_post_saved
            )
            comment_items.append(
                NotificationItem(
                    type=ItemType.comment,
                    created_at=comment.created_at,
                    user=comment.user,
                    item_id=comment.id,
                    post=external_post,
                    comment=Comment(**CommentWithoutLikeStatus.from_orm(comment).dict(), liked=is_comment_liked),
                )
            )
        return comment_items

    async def _get_db_posts(self, post_ids: list[PostId]) -> list[PostRow]:
        posts_query = select(PostRow).options(*eager_load_post_options()).where(PostRow.id.in_(post_ids))
        result = await self.db.execute(posts_query)
        return result.scalars().all()  # type: ignore
