from typing import Optional

from psycopg2.errorcodes import UNIQUE_VIOLATION  # type: ignore
from sqlalchemy import and_, exists, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, undefer

from app.core.types import UserId, ImageId
from app.core.database.models import CommentRow, CommentLikeRow, ImageUploadRow, PostRow, UserRow


def is_comment_liked_query(user_id: UserId):
    """Return a subquery that returns whether the comment in the main query is liked by the given user."""
    return (
        exists()
            .where(and_(CommentLikeRow.comment_id == CommentRow.id, CommentLikeRow.user_id == user_id))
            .label("comment_liked")
    )


def eager_load_post_options():
    """Return the options to eagerly load a post's attributes."""
    return (
        joinedload(PostRow.user, innerjoin=True),
        joinedload(PostRow.user, innerjoin=True).joinedload(UserRow.profile_picture),
        joinedload(PostRow.user, innerjoin=True).undefer(UserRow.post_count),
        joinedload(PostRow.user, innerjoin=True).undefer(UserRow.following_count),
        joinedload(PostRow.user, innerjoin=True).undefer(UserRow.follower_count),
        joinedload(PostRow.place, innerjoin=True),
        joinedload(PostRow.image),
        undefer(PostRow.like_count),
        undefer(PostRow.comment_count),
    )


def eager_load_comment_options():
    """Return the options to eagerly load a comment's attributes."""
    return (
        joinedload(CommentRow.user, innerjoin=True),
        joinedload(CommentRow.user, innerjoin=True).joinedload(UserRow.profile_picture),
        joinedload(CommentRow.user, innerjoin=True).undefer(UserRow.post_count),
        joinedload(CommentRow.user, innerjoin=True).undefer(UserRow.following_count),
        joinedload(CommentRow.user, innerjoin=True).undefer(UserRow.follower_count),
        undefer(CommentRow.like_count),
    )


def eager_load_user_options():
    """Return the options to eagerly load a user's public attributes."""
    return (
        joinedload(UserRow.profile_picture),
        undefer(UserRow.post_count),
        undefer(UserRow.following_count),
        undefer(UserRow.follower_count),
    )


def is_unique_constraint_error(e: IntegrityError, constraint_name: str) -> bool:
    """Return whether the error a unique constraint violation for the given constraint name."""
    # Unfortunately there isn't a cleaner way than parsing the error message
    constraint_msg = f'unique constraint "{constraint_name}"'
    return e.orig.pgcode == UNIQUE_VIOLATION and constraint_msg in str(e)


def is_unique_column_error(e: IntegrityError, column_name: str) -> bool:
    """Return whether the error a unique constraint violation for the given column name."""
    return e.orig.pgcode == UNIQUE_VIOLATION and f"Key ({column_name})" in str(e)


async def get_image_with_lock_else_throw(db: AsyncSession, user_id: UserId, image_id: ImageId) -> ImageUploadRow:
    """Note: This locks the image row. Make sure to unlock by calling db.commit()/db.rollback()."""
    image = await maybe_get_image_with_lock(db, user_id, image_id)
    if image is None:
        raise ValueError("Invalid image")
    return image


async def maybe_get_image_with_lock(db: AsyncSession, user_id: UserId, image_id: ImageId) -> Optional[ImageUploadRow]:
    """
    Note: This locks the image row. Make sure to unlock by calling db.commit()/db.rollback().

    More info on "for update" at: https://www.postgresql.org/docs/current/sql-select.html

    Relevant: "[R]ows that satisfied the query conditions as of the query snapshot will be locked, although they will
    not be returned if they were updated after the snapshot and no longer satisfy the query conditions."

    This means that if this function returns a row, used will be false and remain false until we change it or release
    the lock., preventing the possibility of race conditions (e.g., if two requests come in with same image ID, we
    only allow using the image for one request).
    """
    query = (
        select(ImageUploadRow)
            .where(
            ImageUploadRow.user_id == user_id,
            ImageUploadRow.id == image_id,
            ImageUploadRow.firebase_public_url.isnot(None),
            ~ImageUploadRow.used,
        )
            .with_for_update()
    )
    return (await db.execute(query)).scalars().first()
