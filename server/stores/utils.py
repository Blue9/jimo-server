import uuid
from typing import Optional

from psycopg2.errorcodes import UNIQUE_VIOLATION

from sqlalchemy import and_, exists, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload, undefer, Session

import schemas
from models import models


def is_post_liked_query(user_id: uuid.UUID):
    """Return a subquery that returns whether the post in the main query is liked by the given user."""
    return exists() \
        .where(and_(models.PostLike.post_id == models.Post.id, models.PostLike.user_id == user_id)) \
        .label("post_liked")


def is_comment_liked_query(user_id: uuid.UUID):
    """Return a subquery that returns whether the comment in the main query is liked by the given user."""
    return exists() \
        .where(and_(models.CommentLike.comment_id == models.Comment.id, models.CommentLike.user_id == user_id)) \
        .label("comment_liked")


def rows_to_posts(rows: list[tuple[models.Post, bool]]) -> list[schemas.post.Post]:
    """Convert the list of rows in (post, is_post_liked) format to a list of post objects."""
    schema_posts = []
    for post, is_post_liked in rows:
        fields = schemas.post.ORMPost.from_orm(post).dict()
        schema_posts.append(schemas.post.Post(**fields, liked=is_post_liked))
    return schema_posts


def eager_load_post_options():
    """Return the options to eagerly load a post's attributes."""
    return (
        joinedload(models.Post.user, innerjoin=True),
        joinedload(models.Post.user, innerjoin=True).joinedload(models.User.profile_picture),
        joinedload(models.Post.user, innerjoin=True).undefer(models.User.post_count),
        joinedload(models.Post.user, innerjoin=True).undefer(models.User.following_count),
        joinedload(models.Post.user, innerjoin=True).undefer(models.User.follower_count),
        joinedload(models.Post.place, innerjoin=True),
        joinedload(models.Post.image),
        undefer(models.Post.like_count),
        undefer(models.Post.comment_count)
    )


def eager_load_comment_options():
    """Return the options to eagerly load a comment's attributes."""
    return (
        joinedload(models.Comment.user, innerjoin=True),
        joinedload(models.Comment.user, innerjoin=True).joinedload(models.User.profile_picture),
        joinedload(models.Comment.user, innerjoin=True).undefer(models.User.post_count),
        joinedload(models.Comment.user, innerjoin=True).undefer(models.User.following_count),
        joinedload(models.Comment.user, innerjoin=True).undefer(models.User.follower_count),
        undefer(models.Comment.like_count)
    )


def eager_load_post_except_user_options():
    """Return the options to eagerly load a post's attributes except the user attributes."""
    return (joinedload(models.Post.place, innerjoin=True),
            joinedload(models.Post.image),
            undefer(models.Post.like_count),
            undefer(models.Post.comment_count))


def eager_load_user_options():
    """Return the options to eagerly load a user's public attributes."""
    return (joinedload(models.User.profile_picture),
            undefer(models.User.post_count),
            undefer(models.User.following_count),
            undefer(models.User.follower_count))


def is_unique_constraint_error(e: IntegrityError, constraint_name: str) -> bool:
    """Return whether the error a unique constraint violation for the given constraint name."""
    # Unfortunately there isn't a cleaner way than parsing the error message
    constraint_msg = f'unique constraint "{constraint_name}"'
    return e.orig.pgcode == UNIQUE_VIOLATION and constraint_msg in str(e)


def is_unique_column_error(e: IntegrityError, column_name: str) -> bool:
    """Return whether the error a unique constraint violation for the given column name."""
    return e.orig.pgcode == UNIQUE_VIOLATION and f"Key ({column_name})" in str(e)


def get_image_with_lock_else_throw(db: Session, user_id: uuid.UUID, image_id: uuid.UUID) -> models.ImageUpload:
    """Note: This locks the image row. Make sure to unlock by calling db.commit()/db.rollback()."""
    image = maybe_get_image_with_lock(db, user_id, image_id)
    if image is None:
        raise ValueError("Invalid image")
    return image


def maybe_get_image_with_lock(db: Session, user_id: uuid.UUID, image_id: uuid.UUID) -> Optional[models.ImageUpload]:
    """
    Note: This locks the image row. Make sure to unlock by calling db.commit()/db.rollback().

    More info on "for update" at: https://www.postgresql.org/docs/current/sql-select.html

    Relevant: "[R]ows that satisfied the query conditions as of the query snapshot will be locked, although they will
    not be returned if they were updated after the snapshot and no longer satisfy the query conditions."

    This means that if this function returns a row, used will be false and remain false until we change it or release
    the lock.
    """
    query = select(models.ImageUpload).where(models.ImageUpload.user_id == user_id,
                                             models.ImageUpload.id == image_id,
                                             models.ImageUpload.firebase_public_url.isnot(None),
                                             ~models.ImageUpload.used).with_for_update()
    return db.execute(query).scalars().first()
