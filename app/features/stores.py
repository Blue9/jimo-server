from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database.engine import get_db
from app.features.comments.comment_store import CommentStore
from app.features.map.map_store import MapStore
from app.features.notifications.activity_feed_store import ActivityFeedStore
from app.features.places.place_store import PlaceStore
from app.features.posts.feed_store import FeedStore
from app.features.posts.post_store import PostStore
from app.features.search.search_store import SearchStore
from app.features.users.relation_store import RelationStore
from app.features.users.user_store import UserStore


def get_comment_store(db: AsyncSession = Depends(get_db)):
    return CommentStore(db=db)


def get_feed_store(db: AsyncSession = Depends(get_db)):
    return FeedStore(db=db)


def get_map_store(db: AsyncSession = Depends(get_db)):
    return MapStore(db=db)


def get_notification_store(db: AsyncSession = Depends(get_db)):
    return ActivityFeedStore(db=db)


def get_place_store(db: AsyncSession = Depends(get_db)):
    return PlaceStore(db=db)


def get_post_store(db: AsyncSession = Depends(get_db)):
    return PostStore(db=db)


def get_relation_store(db: AsyncSession = Depends(get_db)):
    return RelationStore(db=db)


def get_user_store(db: AsyncSession = Depends(get_db)):
    return UserStore(db=db)


def get_search_store(db: AsyncSession = Depends(get_db)):
    return SearchStore(db=db)
