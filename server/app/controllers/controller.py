from typing import Optional

from sqlalchemy.orm import Session

from app.controllers import auth
from app.models.models import User, Post, Comment


def get_user(db: Session, username: str):
    return db.query(User).filter(User.username == username).first()


def get_feed(db: Session, user: User, before_post_id: Optional[str] = None) -> Optional[list[Post]]:
    before_post = None
    if before_post_id is not None:
        before_post = db.query(Post).filter(Post.urlsafe_id == before_post_id).first()
        if before_post is None or not auth.user_can_view_post(user, before_post):
            return None
    following_ids = [u.id for u in user.following]
    following_ids.append(user.id)
    query = db.query(Post).filter(Post.user_id.in_(following_ids))
    if before_post is not None:
        query = query.filter(Post.id > before_post.id)
    return query.order_by(Post.created_at.desc()).limit(50).all()


def get_post(db: Session, post_id: str):
    return db.query(Post).filter(Post.urlsafe_id == post_id).first()


def get_comments(db: Session, post_id: str) -> Optional[list[Comment]]:
    post = db.query(Post).filter(Post.urlsafe_id == post_id).first()
    if not post:
        return None
    return post.comments
