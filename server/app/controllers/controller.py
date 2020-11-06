from sqlalchemy.orm import Session

from app.models.models import User, Post


def get_user(db: Session, username: str):
    return db.query(User).filter(User.username == username).first()


def get_feed(db: Session, user: User, page: int):
    offset = (page - 1) * 50
    offset = 0 if offset <= 0 else offset
    following_ids = [u.id for u in user.following]
    following_ids.append(user.id)
    return db.query(Post).filter(
        Post.user_id.in_(following_ids)).order_by(Post.created_at.desc()).offset(offset).limit(50).all()


def get_post(db: Session, post_id: str):
    return db.query(Post).filter(Post.urlsafe_id == post_id).first()
