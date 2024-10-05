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
    image_upload.blob_name = blob_name
    image_upload.url = url
    await db.commit()
    await db.refresh(image_upload)
    return image_upload


async def check_valid_image(file: UploadFile):
    # Read a portion of the file to determine the type and also calculate the size
    file.file.seek(0)
    file_head = await file.read(512)  # Read the first 512 bytes for type detection

    # Use imghdr to determine the file type
    detected_format = imghdr.what(None, file_head)
    if detected_format is None:
        raise HTTPException(400, detail="Unable to determine the image format.")
    elif detected_format not in ["jpeg", "png", "gif", "jpg"]:
        raise HTTPException(400, detail="Unsupported image format.")

    # Now proceed to check the size of the entire file
    file_size = len(file_head)
    while True:
        chunk = await file.read(1024 * 1024)  # Read in 1MB chunks
        if not chunk:
            break
        file_size += len(chunk)
        if file_size > 10 * 1024 * 1024:
            raise HTTPException(400, detail="Max image size is 10MB.")
    
    # Reset the file pointer for further use
    file.file.seek(0)


async def get_images(db: AsyncSession, user_id: UserId, image_ids: list[ImageId]) -> list[ImageUploadRow]:
    if len(image_ids) == 0:
        return []
    query = select(ImageUploadRow).where(
        ImageUploadRow.user_id == user_id,
        ImageUploadRow.id.in_(image_ids),
        ImageUploadRow.url.is_not(None),
    )
    rows = (await db.execute(query)).scalars().all()
    rows_by_id = {image.id: image for image in rows}
    return [rows_by_id[id] for id in image_ids if id in rows_by_id]


async def get_image_else_throw(db: AsyncSession, user_id: UserId, image_id: ImageId) -> ImageUploadRow:
    image = await maybe_get_image(db, user_id, image_id)
    if image is None:
        raise ValueError("Invalid image")
    return image


async def maybe_get_image(db: AsyncSession, user_id: UserId, image_id: ImageId) -> Optional[ImageUploadRow]:
    query = select(ImageUploadRow).where(
        ImageUploadRow.user_id == user_id,
        ImageUploadRow.id == image_id,
        ImageUploadRow.url.is_not(None),
    )
    return (await db.execute(query)).scalars().first()
