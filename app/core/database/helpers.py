from psycopg2.errorcodes import UNIQUE_VIOLATION  # type: ignore
from sqlalchemy import and_, exists
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload, undefer

from app.core.types import UserId
from app.core.database.models import CommentRow, CommentLikeRow, PostRow, UserRow


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
