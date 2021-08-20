import uuid
from typing import Optional

from fastapi import Depends
from sqlalchemy import select, exists, update, func, delete
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import schemas
from app.controllers import utils, categories, images
from app.db.database import get_db
from app.models import models


class PostStore:
    def __init__(self, db: Session = Depends(get_db)):
        self.db = db

    # Scalar queries

    def already_posted(self, user_id: uuid.UUID, place_id: uuid.UUID):
        """Return true if the user already posted this place, false otherwise."""
        query = select(models.Post) \
            .where(models.Post.user_id == user_id, models.Post.place_id == place_id, ~models.Post.deleted)
        return self.db.execute(exists(query).select()).scalar()

    def get_like_count(self, post_id: uuid.UUID):
        """Return the like count of the given post."""
        query = select(func.count()).select_from(models.PostLike).where(models.PostLike.post_id == post_id)
        return self.db.execute(query).scalar()

    def post_exists(self, post_id: uuid.UUID):
        """Return whether the post exists and is not deleted."""
        query = select(models.Post.id).where(models.Post.id == post_id, ~models.Post.deleted)
        return self.db.execute(exists(query).select()).scalar()

    # Queries

    def get_post(self, post_id: uuid.UUID) -> Optional[schemas.internal.InternalPost]:
        """Return the post with the given id or None if no such post exists or the post is deleted."""
        query = select(models.Post).where(models.Post.id == post_id, ~models.Post.deleted)
        post = self.db.execute(query).scalars().first()
        return schemas.internal.InternalPost.from_orm(post) if post else None

    def get_posts(
        self,
        caller_user_id: uuid.UUID,
        user: schemas.internal.InternalUser,
        cursor: Optional[uuid.UUID],
        limit: int = 50
    ) -> list[schemas.post.Post]:
        """Get the user's posts that aren't deleted."""
        user_posts_query = select(models.Post, utils.is_post_liked_query(caller_user_id)) \
            .options(*utils.eager_load_post_except_user_options()) \
            .where(models.Post.user_id == user.id, ~models.Post.deleted)
        if cursor:
            user_posts_query = user_posts_query.where(models.Post.id < cursor)
        rows = self.db.execute(user_posts_query.order_by(models.Post.id.desc()).limit(limit)).all()
        user_posts = []
        for post, is_post_liked in rows:
            # ORMPostWithoutUser avoids querying post.user; we already know the user
            fields = schemas.post.ORMPostWithoutUser.from_orm(post).dict()
            user_posts.append(schemas.post.Post(**fields, user=user, liked=is_post_liked))
        return user_posts

    def get_place_name(self, post_id: uuid.UUID) -> str:
        place_name_query = select(models.Place.name) \
            .join(models.Post) \
            .where(models.Post.id == post_id, ~models.Post.deleted, models.Post.place_id == models.Place.id)
        place_name = self.db.execute(place_name_query).scalars().first()
        return place_name if place_name is not None else ""

    def get_mutual_posts(self, user_id: uuid.UUID, place_id: uuid.UUID, limit: int = 100) -> list[schemas.post.Post]:
        following_ids = select(models.UserRelation.to_user_id).where(
            (models.UserRelation.from_user_id == user_id) & (
                models.UserRelation.relation == models.UserRelationType.following))
        query = select(models.Post, exists()
                       .where((models.PostLike.post_id == models.Post.id) & (models.PostLike.user_id == user_id))
                       .label("post_liked")) \
            .join(models.Place) \
            .where(models.Place.id == place_id) \
            .where(models.Post.user_id.in_(following_ids) | (models.Post.user_id == user_id)) \
            .where(~models.Post.deleted) \
            .order_by(models.Post.created_at.desc()) \
            .limit(limit)
        result = self.db.execute(query).all()
        posts = []
        for post, is_post_liked in result:
            fields = schemas.post.ORMPost.from_orm(post).dict()
            posts.append(schemas.post.Post(**fields, liked=is_post_liked))
        return posts

    # Operations

    def create_post(
        self,
        user_id: uuid.UUID,
        place_id: uuid.UUID,
        request: schemas.post.CreatePostRequest
    ) -> schemas.post.ORMPost:
        """Try to create a post with the given details, raising a ValueError if the request is invalid."""
        category = categories.get_category_or_raise(self.db, request.category)
        if self.already_posted(user_id, place_id):
            raise ValueError("You already posted that place.")
        image = images.get_image_with_lock_else_throw(
            self.db, user_id, request.image_id) if request.image_id is not None else None
        custom_latitude = request.custom_location.latitude if request.custom_location else None
        custom_longitude = request.custom_location.longitude if request.custom_location else None
        post = models.Post(user_id=user_id, place_id=place_id, category=category, custom_latitude=custom_latitude,
                           custom_longitude=custom_longitude, content=request.content,
                           image_id=image.id if image else None)
        try:
            if image:
                image.used = True
            self.db.add(post)
            self.db.commit()
            return schemas.post.ORMPost.from_orm(post)
        except IntegrityError as e:
            self.db.rollback()
            if utils.is_unique_constraint_error(e, models.Post.user_place_uc):
                raise ValueError("You already posted that place.")
            elif utils.is_unique_column_error(e, models.Post.image_id.key):
                raise ValueError("Duplicate image.")
            else:
                print(e)
                raise ValueError("Could not create post.")

    def delete_post(self, post_id: uuid.UUID):
        """Mark the given post as deleted."""
        self.db.execute(update(models.Post).where(models.Post.id == post_id).values(deleted=True))
        self.db.commit()

    def like_post(self, user_id: uuid.UUID, post_id: uuid.UUID):
        """Like the given post."""
        post_like = models.PostLike(user_id=user_id, post_id=post_id)
        self.db.add(post_like)
        try:
            self.db.commit()
        except IntegrityError:
            # Ignore error when trying to like a post twice
            self.db.rollback()
            return

    def unlike_post(self, user_id: uuid.UUID, post_id: uuid.UUID):
        """Unlike the given post."""
        query = delete(models.PostLike).where(models.PostLike.user_id == user_id, models.PostLike.post_id == post_id)
        self.db.execute(query)
        self.db.commit()

    def report_post(self, post_id: uuid.UUID, reported_by: uuid.UUID, details: Optional[str]) -> bool:
        report = models.PostReport(post_id=post_id, reported_by_user_id=reported_by, details=details)
        try:
            self.db.add(report)
            self.db.commit()
            return True
        except IntegrityError:
            self.db.rollback()
            return False
