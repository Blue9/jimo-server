from datetime import datetime
from typing import Optional

from app.features.places.entities import Place
from app.core.types import InternalBase, UserId, PostSaveId, PostId, CommentId, ImageId


class InternalUser(InternalBase):
    id: UserId
    uid: str
    username: str
    username_lower: str
    first_name: str
    last_name: str
    phone_number: Optional[str]
    profile_picture_id: Optional[ImageId]
    profile_picture_url: Optional[str]
    profile_picture_blob_name: Optional[str]
    is_featured: bool
    is_admin: bool
    deleted: bool
    created_at: datetime
    updated_at: datetime
    post_count: int
    follower_count: int
    following_count: int


class InternalPost(InternalBase):
    id: PostId
    user_id: UserId
    place: Place
    category: str
    custom_latitude: Optional[float]
    custom_longitude: Optional[float]
    content: str
    image_id: Optional[ImageId]
    image_url: Optional[str]
    image_blob_name: Optional[str]
    deleted: bool
    created_at: datetime
    like_count: int
    comment_count: int


class InternalComment(InternalBase):
    id: CommentId
    user_id: UserId
    post_id: PostId
    content: str
    deleted: bool
    created_at: datetime


class InternalPostSave(InternalBase):
    id: PostSaveId
    user_id: UserId
    post_id: PostId
