from typing import Optional

from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.controllers import places, utils
from app.models.models import Post, Comment, User, Place, Category, post_like
from app.models.request_schemas import CreatePostRequest


def get_post(db: Session, post_id: str):
    """Return the post with the given urlsafe_id or None if no such post exists."""
    return db.query(Post).filter(Post.urlsafe_id == post_id).first()


def get_category_or_raise(db: Session, category_name: str) -> Category:
    """Get the category model for the given category name."""
    category = db.query(Category).filter(Category.name == category_name).first()
    if category is None:
        raise ValueError("Invalid category")
    return category


def already_posted(db: Session, user: User, place: Place):
    """Return true if the user already posted this place, false otherwise."""
    existing_post = db.query(Post).filter(and_(Post.user_id == user.id, Post.place_id == place.id)).first()
    return existing_post is not None


def get_comments(db: Session, post_id: str) -> Optional[list[Comment]]:
    """Get the comments for the given post, returning None if no such post exists."""
    post = db.query(Post).filter(Post.urlsafe_id == post_id).first()
    if not post:
        return None
    return post.comments


def like_post(db: Session, user: User, post: Post):
    """Like the given post."""
    # TODO(gmekkat) make sure this is fine
    post.likes.append(user)
    db.commit()


def unlike_post(db: Session, user: User, post: Post):
    """Unlike the given post."""
    unlike = post_like.delete().where(and_(post_like.c.user_id == user.id, post_like.c.post_id == post.id))
    db.execute(unlike)
    db.commit()


def create_post(db: Session, user: User, request: CreatePostRequest) -> Optional[Post]:
    """Try to create a post with the given details, raising a ValueError if the request is invalid."""
    category = get_category_or_raise(db, request.category)
    place = places.get_place_or_create(db, request.place)
    if already_posted(db, user, place):
        raise ValueError("You already posted that place.")
    custom_latitude = request.custom_location.latitude if request.custom_location else None
    custom_longitude = request.custom_location.longitude if request.custom_location else None
    build_post = lambda url_id: Post(urlsafe_id=url_id, user_id=user.id, place_id=place.id, category_id=category.id,
                                     custom_latitude=custom_latitude, custom_longitude=custom_longitude,
                                     content=request.content, image_url=request.image_url)
    return utils.add_with_urlsafe_id(db, build_post)