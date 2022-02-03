import imghdr
import uuid
from typing import Optional

from shared import schemas
from sqlalchemy.ext.asyncio import AsyncSession

from app import config
from app.db.database import get_db
from shared.stores.comment_store import CommentStore
from shared.stores.feed_store import FeedStore
from shared.stores.invite_store import InviteStore
from shared.stores.place_store import PlaceStore
from shared.stores.post_store import PostStore
from shared.stores.relation_store import RelationStore
from shared.stores.user_store import UserStore
from fastapi import HTTPException, UploadFile, Depends
from sqlalchemy.exc import IntegrityError

from app.controllers.firebase import FirebaseAdminProtocol
from shared.models import models


async def validate_user(
    relation_store: RelationStore,
    caller_user_id: uuid.UUID,
    user: Optional[schemas.internal.InternalUser]
) -> schemas.internal.InternalUser:
    if user is None or user.deleted or await relation_store.is_blocked(
        blocked_by_user_id=user.id,
        blocked_user_id=caller_user_id
    ):
        raise HTTPException(404, detail="User not found")
    return user


async def get_user_from_uid_or_raise(user_store: UserStore, uid: str) -> schemas.internal.InternalUser:
    user: Optional[schemas.internal.InternalUser] = await user_store.get_user_by_uid(uid)
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
    current_user: schemas.internal.InternalUser,
    post_ids: list[uuid.UUID],
    post_store: PostStore,
    place_store: PlaceStore,
    user_store: UserStore,
) -> list[schemas.post.Post]:
    # Step 1: Get internal posts
    internal_posts = await post_store.get_posts(post_ids)
    # Step 2: Get places
    place_ids = set(post.place_id for post in internal_posts)
    places = await place_store.get_places(place_ids)
    # Step 3: Get like statuses for each post
    liked_post_ids = await post_store.get_liked_posts(current_user.id, post_ids)
    # Step 4: Get users for each post
    user_ids = list(set(post.user_id for post in internal_posts))
    users: dict[uuid.UUID, schemas.internal.InternalUser] = await user_store.get_users(user_ids=user_ids)

    posts = []
    for post in internal_posts:
        public_post = schemas.post.Post(
            id=post.id,
            place=places[post.place_id],
            category=post.category,
            content=post.content,
            image_url=post.image_url,
            created_at=post.created_at,
            like_count=post.like_count,
            comment_count=post.comment_count,
            user=users[post.user_id],
            liked=post.id in liked_post_ids
        )
        posts.append(public_post)
    return posts


async def upload_image(
    file: UploadFile,
    user: schemas.internal.InternalUser,
    firebase_admin: FirebaseAdminProtocol,
    db: AsyncSession
) -> models.ImageUpload:
    await check_valid_image(file)
    # Set override_used to True if you plan to immediately use the image in a profile picture or post (as opposed to
    # returning the image ID to the user).
    image_upload: models.ImageUpload = models.ImageUpload(user_id=user.id, used=False)
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
    post_id: uuid.UUID
) -> schemas.internal.InternalPost:
    """
    Check that the post exists and the given user is authorized to view it.

    Note: if the user is not authorized (the author blocked the caller user or has been blocked by the caller user),
    a 404 will be returned because they shouldn't even know that the post exists.
    """
    post: Optional[schemas.internal.InternalPost] = await post_store.get_post(post_id)
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


def get_invite_store(db: AsyncSession = Depends(get_db)):
    return InviteStore(invites_per_user=config.INVITES_PER_USER, db=db)


def get_place_store(db: AsyncSession = Depends(get_db)):
    return PlaceStore(db=db)


def get_post_store(db: AsyncSession = Depends(get_db)):
    return PostStore(db=db)


def get_relation_store(db: AsyncSession = Depends(get_db)):
    return RelationStore(db=db)


def get_user_store(db: AsyncSession = Depends(get_db)):
    return UserStore(db=db)
