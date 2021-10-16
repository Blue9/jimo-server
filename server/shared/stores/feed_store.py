import datetime
import uuid
from typing import Optional

from sqlalchemy import union_all, select, exists
from sqlalchemy.orm import Session, aliased, joinedload

from shared import schemas
from shared.stores import utils
from shared.models import models
from shared.schemas.comment import ORMComment
from shared.schemas.notifications import NotificationItem, ItemType
from shared.schemas.post import ORMPost


class FeedStore:
    def __init__(self, db: Session):
        self.db = db

    def get_feed(
        self,
        user_id: uuid.UUID,
        cursor: Optional[uuid.UUID] = None,
        limit: int = 50
    ) -> list[schemas.post.Post]:
        """Get the user's feed, returning None if the user is not authorized or if before_post_id is invalid."""
        query = self._feed_query(user_id)
        if cursor:
            query = query.where(models.Post.id < cursor)
        rows = self.db.execute(query.order_by(models.Post.id.desc()).limit(limit)).all()
        return utils.rows_to_posts(rows)

    def _feed_query(self, user_id: uuid.UUID):
        followed_users_subquery = select(models.UserRelation.to_user_id) \
            .where(models.UserRelation.from_user_id == user_id,
                   models.UserRelation.relation == models.UserRelationType.following)
        return select(models.Post, utils.is_post_liked_query(user_id)) \
            .options(*utils.eager_load_post_options()) \
            .where((models.Post.user_id == user_id) | models.Post.user_id.in_(followed_users_subquery)) \
            .where(~models.Post.deleted) \
            .order_by(models.Post.id.desc())

    def get_discover_feed(self, user_id: uuid.UUID) -> list[schemas.post.Post]:
        """Get the user's discover feed."""
        one_week_ago = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(weeks=1)
        # TODO also filter by Post.user_id != user.id, for now it's easier to test without
        blocked_subquery = union_all(
            select(models.UserRelation.from_user_id).select_from(models.UserRelation).where(
                models.UserRelation.to_user_id == user_id,
                models.UserRelation.relation == models.UserRelationType.blocked),
            select(models.UserRelation.to_user_id).select_from(models.UserRelation).where(
                models.UserRelation.from_user_id == user_id,
                models.UserRelation.relation == models.UserRelationType.blocked)
        )
        query = select(models.Post, utils.is_post_liked_query(user_id)) \
            .options(*utils.eager_load_post_options()) \
            .where(models.Post.user_id.notin_(blocked_subquery),
                   models.Post.image_id.isnot(None),
                   models.Post.created_at > one_week_ago,
                   ~models.Post.deleted) \
            .order_by(models.Post.like_count.desc()) \
            .limit(300)
        rows = self.db.execute(query).all()
        return utils.rows_to_posts(rows)

    def get_follow_feed(
        self,
        user_id, cursor: Optional[uuid.UUID] = None,
        limit: int = 50
    ) -> list[NotificationItem]:
        follow_query = select(models.UserRelation, models.User) \
            .options(*utils.eager_load_user_options()) \
            .where(models.UserRelation.to_user_id == user_id,
                   models.User.id == models.UserRelation.from_user_id,
                   models.UserRelation.relation == models.UserRelationType.following,
                   ~models.User.deleted)
        if cursor is not None:
            follow_query = follow_query.where(models.UserRelation.id < cursor)
        follow_results = self.db.execute(follow_query.order_by(models.UserRelation.id.desc()).limit(limit)).all()
        follow_items = []
        for f in follow_results:
            follow_items.append(NotificationItem(type=ItemType.follow, created_at=f.UserRelation.created_at,
                                                 user=f.User, item_id=f.UserRelation.id))
        return follow_items

    def get_post_like_feed(
        self,
        user_id,
        cursor: Optional[uuid.UUID] = None,
        limit: int = 50
    ) -> list[NotificationItem]:
        post_like_alias = aliased(models.PostLike)
        like_query = select(models.PostLike,
                            models.Post,
                            exists().where((post_like_alias.post_id == models.Post.id)
                                           & (post_like_alias.user_id == user_id)).label("post_liked")) \
            .options(joinedload(models.PostLike.liked_by).options(*utils.eager_load_user_options()),
                     *utils.eager_load_post_options()) \
            .where(models.PostLike.post_id == models.Post.id,
                   models.Post.user_id == user_id,
                   ~models.Post.deleted,
                   user_id != models.PostLike.user_id,
                   models.PostLike.liked_by.has(deleted=False))
        if cursor is not None:
            like_query = like_query.where(models.PostLike.id < cursor)

        like_results = self.db.execute(like_query.order_by(models.PostLike.id.desc()).limit(limit)).all()
        like_items = []

        for post_like, post, is_post_liked in like_results:
            fields = ORMPost.from_orm(post).dict()
            like_items.append(NotificationItem(type=ItemType.like, created_at=post_like.created_at,
                                               user=post_like.liked_by, item_id=post_like.id,
                                               post=schemas.post.Post(**fields, liked=is_post_liked)))
        return like_items

    def get_comment_feed(
        self,
        user_id,
        cursor: Optional[uuid.UUID] = None,
        limit: int = 50
    ) -> list[NotificationItem]:
        comment_query = select(models.Comment, utils.is_comment_liked_query(user_id)) \
            .options(*utils.eager_load_comment_options()) \
            .join(models.Post) \
            .where(models.Comment.post_id == models.Post.id,
                   models.Post.user_id == user_id,
                   models.Comment.user_id != user_id,
                   ~models.Comment.deleted,
                   ~models.Post.deleted,
                   models.Comment.user.has(deleted=False))
        if cursor:
            comment_query = comment_query.where(models.Comment.id < cursor)
        comment_rows = self.db.execute(comment_query.order_by(models.Comment.id.desc()).limit(limit)).all()
        post_ids = set(row.Comment.post_id for row in comment_rows)
        comment_items = []
        posts_query = select(models.Post, utils.is_post_liked_query(user_id)) \
            .options(*utils.eager_load_post_options()) \
            .where(models.Post.id.in_(post_ids))
        posts = self.db.execute(posts_query).all()
        post_rows_by_id = {post.Post.id: post for post in posts}
        for row in comment_rows:
            comment: models.Comment = row.Comment
            post_row = post_rows_by_id.get(comment.post_id)
            if post_row is None:  # Should never happen but just in case
                continue
            post: models.Post = post_row.Post
            is_post_liked: bool = post_row.post_liked
            is_comment_liked: bool = row.comment_liked
            comment_items.append(
                NotificationItem(
                    type=ItemType.comment, created_at=comment.created_at, user=comment.user, item_id=comment.id,
                    post=schemas.post.Post(**ORMPost.from_orm(post).dict(), liked=is_post_liked),
                    comment=schemas.comment.Comment(**ORMComment.from_orm(comment).dict(), liked=is_comment_liked)
                )
            )
        return comment_items

    def get_notification_feed(
        self,
        user_id: uuid.UUID,
        cursor: Optional[uuid.UUID] = None,
        limit: int = 50
    ) -> list[NotificationItem]:
        follow_feed = self.get_follow_feed(user_id, cursor, limit)
        post_like_feed = self.get_post_like_feed(user_id, cursor, limit)
        comment_feed = self.get_comment_feed(user_id, cursor, limit)
        return sorted(follow_feed + post_like_feed + comment_feed, key=lambda i: i.item_id, reverse=True)[:limit]
