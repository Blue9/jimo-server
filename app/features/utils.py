import imghdr
import uuid
from typing import Optional

from fastapi import HTTPException, UploadFile, Depends
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database.engine import get_db
from app.core.database.models import ImageUploadRow
from app.core.firebase import FirebaseAdminProtocol
from app.core.internal import InternalUser, InternalPost
from app.core.types import UserId, PlaceId
from app.features.comments.comment_store import CommentStore
from app.features.map.map_store import MapStore
from app.features.notifications.notification_store import NotificationStore
from app.features.places.place_store import PlaceStore
from app.features.posts.entities import Post
from app.features.posts.feed_store import FeedStore
from app.features.posts.post_store import PostStore
from app.features.posts.types import MaybeCreatePlaceRequest
from app.features.users.relation_store import RelationStore
from app.features.users.user_store import UserStore


async def validate_user(
    relation_store: RelationStore,
    caller_user_id: uuid.UUID,
    user: Optional[InternalUser],
) -> InternalUser:
    if (
        user is None
        or user.deleted
        or await relation_store.is_blocked(blocked_by_user_id=user.id, blocked_user_id=caller_user_id)
    ):
        raise HTTPException(404, detail="User not found")
    return user


async def get_user_from_uid_or_raise(user_store: UserStore, uid: str) -> InternalUser:
    user: Optional[InternalUser] = await user_store.get_user_by_uid(uid)
    if user is None or user.deleted:
        raise HTTPException(403)
    return user


async def check_valid_image(file: UploadFile):
    if file.content_type != "image/jpeg" or imghdr.what(file.file) != "jpeg":
        raise HTTPException(400, detail="File must be a jpeg")
    file_size = 0
    for chunk in file.file:
        file_size += len(chunk)
        if file_size > 2 * 1024 * 1024:
            raise HTTPException(400, detail="Max file size is 2MB")
    file.file.seek(0)


async def get_posts_from_post_ids(
    current_user: InternalUser,
    post_ids: list[uuid.UUID],
    post_store: PostStore,
    place_store: PlaceStore,
    user_store: UserStore,
    preserve_order=False,
) -> list[Post]:
    # Step 1: Get internal posts
    internal_posts = await post_store.get_posts(post_ids, preserve_order=preserve_order)
    # Step 2: Get like and save statuses for each post
    liked_post_ids = await post_store.get_liked_posts(current_user.id, post_ids)
    saved_post_ids = await post_store.get_saved_posts(current_user.id, post_ids)
    # Step 3: Get users for each post
    user_ids = list(set(post.user_id for post in internal_posts))
    users: dict[uuid.UUID, InternalUser] = await user_store.get_users(user_ids=user_ids)

    posts = []
    for post in internal_posts:
        place = post.place
        user = users.get(post.user_id)
        if user is None:
            continue
        public_post = Post(
            id=post.id,
            place=place,
            category=post.category,
            content=post.content,
            image_id=post.image_id,
            image_url=post.image_url,
            created_at=post.created_at,
            like_count=post.like_count,
            comment_count=post.comment_count,
            user=user,
            liked=post.id in liked_post_ids,
            saved=post.id in saved_post_ids,
        )
        posts.append(public_post)
    return posts


async def get_or_create_place(
    user_id: UserId,
    request: MaybeCreatePlaceRequest,
    place_store: PlaceStore,
) -> PlaceId:
    loc = request.location
    radius = request.region.radius if request.region else 10
    place = await place_store.get_or_create_place(
        name=request.name,
        latitude=loc.latitude,
        longitude=loc.longitude,
        search_radius_meters=radius,
    )
    # Update place data
    region = request.region
    additional_data = request.additional_data
    await place_store.maybe_create_place_data(user_id, place.id, region, additional_data)
    return place.id


async def upload_image(
    file: UploadFile,
    user: InternalUser,
    firebase_admin: FirebaseAdminProtocol,
    db: AsyncSession,
) -> ImageUploadRow:
    await check_valid_image(file)
    # Set override_used to True if you plan to immediately use the image in a profile picture or post (as opposed to
    # returning the image ID to the user).
    image_upload = ImageUploadRow(user_id=user.id, used=False)
    try:
        db.add(image_upload)
        await db.commit()
        await db.refresh(image_upload)
    except IntegrityError:
        # Right now this only happens in the case of a UUID collision which should be almost impossible
        raise HTTPException(400, detail="Could not upload image")
    response = await firebase_admin.upload_image(user.uid, image_id=image_upload.id, file_obj=file.file)
    if response is None:
        await db.delete(image_upload)
        await db.commit()
        raise HTTPException(500, detail="Failed to upload image")
    blob_name, url = response
    image_upload.firebase_blob_name = blob_name
    image_upload.firebase_public_url = url
    await db.commit()
    await db.refresh(image_upload)
    return image_upload


async def get_post_and_validate_or_raise(
    post_store: PostStore,
    relation_store: RelationStore,
    caller_user_id: uuid.UUID,
    post_id: uuid.UUID,
) -> InternalPost:
    """
    Check that the post exists and the given user is authorized to view it.

    Note: if the user is not authorized (the author blocked the caller user or has been blocked by the caller user),
    a 404 will be returned because they shouldn't even know that the post exists.
    """
    post: Optional[InternalPost] = await post_store.get_post(post_id)
    if post is None:
        raise HTTPException(404, detail="Post not found")
    if await relation_store.is_blocked(post.user_id, caller_user_id):
        raise HTTPException(404, detail="Post not found")
    if await relation_store.is_blocked(caller_user_id, post.user_id):
        raise HTTPException(404, detail="Post not found")
    return post


def get_comment_store(db: AsyncSession = Depends(get_db)):
    return CommentStore(db=db)


def get_feed_store(db: AsyncSession = Depends(get_db)):
    return FeedStore(db=db)


def get_map_store(db: AsyncSession = Depends(get_db)):
    return MapStore(db=db)


def get_notification_store(db: AsyncSession = Depends(get_db)):
    return NotificationStore(db=db)


def get_place_store(db: AsyncSession = Depends(get_db)):
    return PlaceStore(db=db)


def get_post_store(db: AsyncSession = Depends(get_db)):
    return PostStore(db=db)


def get_relation_store(db: AsyncSession = Depends(get_db)):
    return RelationStore(db=db)


def get_user_store(db: AsyncSession = Depends(get_db)):
    return UserStore(db=db)
