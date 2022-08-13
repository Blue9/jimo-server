import imghdr
from typing import Optional

from fastapi import UploadFile, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database.models import ImageUploadRow
from app.core.firebase import FirebaseAdminProtocol
from app.features.users.entities import InternalUser
from app.core.types import UserId, ImageId


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


async def check_valid_image(file: UploadFile):
    if file.content_type != "image/jpeg" or imghdr.what(file.file) != "jpeg":
        raise HTTPException(400, detail="File must be a jpeg")
    file_size = 0
    for chunk in file.file:
        file_size += len(chunk)
        if file_size > 2 * 1024 * 1024:
            raise HTTPException(400, detail="Max file size is 2MB")
    file.file.seek(0)


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
