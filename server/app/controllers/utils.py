from psycopg2.errorcodes import UNIQUE_VIOLATION

from sqlalchemy import and_, exists
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload, undefer

from app import schemas
from app.models import models


def is_post_liked_query(user: models.User):
    """Return a subquery that returns whether the post in the main query is liked by the given user."""
    return exists() \
        .where(and_(models.PostLike.post_id == models.Post.id, models.PostLike.user_id == user.id)) \
        .label("post_liked")


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
        joinedload(models.Post.user),
        joinedload(models.Post.user).joinedload(models.User.profile_picture),
        joinedload(models.Post.user).undefer(models.User.post_count),
        joinedload(models.Post.user).undefer(models.User.following_count),
        joinedload(models.Post.user).undefer(models.User.follower_count),
        joinedload(models.Post.place),
        joinedload(models.Post.image),
        undefer(models.Post.like_count)
    )


def eager_load_post_except_user_options():
    """Return the options to eagerly load a post's attributes except the user attributes."""
    return (joinedload(models.Post.place),
            joinedload(models.Post.image),
            undefer(models.Post.like_count))


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
