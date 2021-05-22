import datetime
import uuid
from typing import Optional

from fastapi import Depends
from sqlalchemy import union_all, select, exists
from sqlalchemy.orm import Session, aliased

from app import schemas
from app.controllers import utils
from app.db.database import get_db
from app.models import models
from app.schemas.notifications import NotificationItem, ItemType
from app.schemas.post import ORMPost


class FeedStore:
    def __init__(self, db: Session = Depends(get_db)):
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
            query = query.filter(models.Post.id < cursor)
        rows = query.order_by(models.Post.id.desc()).limit(limit).all()
        return utils.rows_to_posts(rows)

    def _feed_query(self, user_id: uuid.UUID):
        followed_users_subquery = select(models.UserRelation.to_user_id) \
            .where(models.UserRelation.from_user_id == user_id,
                   models.UserRelation.relation == models.UserRelationType.following)
        return self.db.query(models.Post, utils.is_post_liked_query(user_id)) \
            .options(utils.eager_load_post_options()) \
            .filter((models.Post.user_id == user_id) | models.Post.user_id.in_(followed_users_subquery)) \
            .filter(~models.Post.deleted) \
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
        rows = self.db.query(models.Post, utils.is_post_liked_query(user_id)) \
            .options(utils.eager_load_post_options()) \
            .filter(models.Post.user_id.notin_(blocked_subquery),
                    models.Post.image_id.isnot(None),
                    models.Post.created_at > one_week_ago,
                    ~models.Post.deleted) \
            .order_by(models.Post.like_count.desc()) \
            .limit(300) \
            .all()
        return utils.rows_to_posts(rows)

    def get_notification_feed(
        self,
        user_id: uuid.UUID,
        cursor: Optional[uuid.UUID] = None,
        limit: int = 50
    ) -> list[NotificationItem]:
        follow_query = self.db.query(models.UserRelation, models.User).filter(
            models.UserRelation.to_user_id == user_id,
            models.User.id == models.UserRelation.from_user_id,
            models.UserRelation.relation == models.UserRelationType.following,
            ~models.User.deleted)
        if cursor is not None:
            follow_query = follow_query.filter(models.UserRelation.id < cursor)

        post_like_alias = aliased(models.PostLike)
        like_query = self.db.query(
            models.PostLike,
            models.Post,
            models.User,
            exists().where((post_like_alias.post_id == models.Post.id)
                           & (post_like_alias.user_id == user_id)).label("post_liked")
        ).filter(
            models.PostLike.post_id == models.Post.id,
            models.Post.user_id == user_id,
            ~models.Post.deleted,
            models.User.id == models.PostLike.user_id,
            models.User.id != user_id,
            ~models.User.deleted
        )
        if cursor is not None:
            like_query = like_query.filter(models.PostLike.id < cursor)

        follow_results = follow_query.order_by(models.UserRelation.id.desc()).limit(limit).all()
        like_results = like_query.order_by(models.PostLike.id.desc()).limit(limit).all()

        follow_items = []
        like_items = []

        for f in follow_results:
            follow_items.append(NotificationItem(type=ItemType.follow, created_at=f.UserRelation.created_at,
                                                 user=f.User, item_id=f.UserRelation.id))
        for like in like_results:
            fields = ORMPost.from_orm(like.Post).dict()
            like_items.append(NotificationItem(type=ItemType.like, created_at=like.PostLike.created_at,
                                               user=like.User, item_id=like.PostLike.id,
                                               post=schemas.post.Post(**fields, liked=like.post_liked)))
        return sorted(follow_items + like_items, key=lambda i: i.item_id, reverse=True)[:limit]
