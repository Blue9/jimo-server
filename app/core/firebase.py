import functools
import uuid
from asyncio import get_event_loop
from dataclasses import dataclass
from typing import Optional, IO, Tuple, Protocol

import firebase_admin  # type: ignore
from fastapi import Header, HTTPException
from firebase_admin import auth, storage
from firebase_admin.auth import (  # type: ignore
    InvalidIdTokenError,
    ExpiredIdTokenError,
    RevokedIdTokenError,
    CertificateFetchError,
    UserNotFoundError,
)
from firebase_admin.exceptions import FirebaseError  # type: ignore
from google.cloud.exceptions import GoogleCloudError
from google.cloud.storage import Bucket  # type: ignore

from app.core import config
from app.utils import get_logger

log = get_logger(__name__)


class FirebaseAdminProtocol(Protocol):
    async def get_uid_from_token(self, id_token: str) -> Optional[str]:
        ...

    async def get_phone_number_from_uid(self, uid: str) -> Optional[str]:
        ...

    async def get_email_from_uid(self, uid: str) -> Optional[str]:
        ...

    async def get_uid_from_auth_header(self, authorization: Optional[str]) -> Optional[str]:
        ...

    async def upload_image(self, user_uid: str, image_id: uuid.UUID, file_obj: IO) -> Optional[Tuple[str, str]]:
        ...

    async def make_image_private(self, blob_name: str):
        ...

    async def make_image_public(self, blob_name: str):
        ...

    async def delete_image(self, blob_name: str):
        ...

    async def delete_user_images(self, user_uid: str):
        ...


class FirebaseAdmin(FirebaseAdminProtocol):
    def __init__(self):
        self._app = firebase_admin.initialize_app(options={"storageBucket": config.STORAGE_BUCKET})

    async def get_uid_from_token(self, id_token: str) -> Optional[str]:
        """Get the user's uid from the given Firebase id token."""
        loop = get_event_loop()
        try:
            decoded_token = await loop.run_in_executor(None, auth.verify_id_token, id_token, self._app)
            return decoded_token.get("uid")
        except (
            ValueError,
            InvalidIdTokenError,
            ExpiredIdTokenError,
            RevokedIdTokenError,
            CertificateFetchError,
        ):
            return None
        except Exception:  # noqa
            log.exception("Unexpected exception")
            return None

    async def get_phone_number_from_uid(self, uid: str) -> Optional[str]:
        loop = get_event_loop()
        try:
            firebase_user = await loop.run_in_executor(None, auth.get_user, uid, self._app)
            return firebase_user.phone_number
        except (ValueError, UserNotFoundError, FirebaseError):
            return None

    async def get_email_from_uid(self, uid: str) -> Optional[str]:
        loop = get_event_loop()
        try:
            firebase_user = await loop.run_in_executor(None, auth.get_user, uid, self._app)
            return firebase_user.email
        except (ValueError, UserNotFoundError, FirebaseError):
            return None

    async def get_uid_from_auth_header(self, authorization: Optional[str]) -> Optional[str]:
        """Get the user's uid from the given authorization header."""
        if authorization is None or not authorization.startswith("Bearer "):
            return None
        id_token = authorization[7:]
        return await self.get_uid_from_token(id_token)

    # Storage
    async def upload_image(self, user_uid: str, image_id: uuid.UUID, file_obj: IO) -> tuple[str, str] | None:
        """Upload the given image to Firebase, returning the blob name and public URL if uploading was successful."""
        loop = get_event_loop()
        bucket = storage.bucket(app=self._app)
        blob = bucket.blob(f"images/{user_uid}/{image_id}.jpg")
        # Known issue in firebase, this metadata is necessary to view images via Firebase console
        blob.metadata = {"firebaseStorageDownloadTokens": uuid.uuid4()}
        try:
            await loop.run_in_executor(
                None,
                functools.partial(blob.upload_from_file, file_obj, content_type="image/jpeg"),
            )
        except GoogleCloudError:
            log.exception("Failed to upload image")
            return None
        await loop.run_in_executor(None, blob.make_public)
        return blob.name, blob.public_url  # type: ignore

    async def make_image_private(self, blob_name: str):
        """Revoke read access for anonymous users. Used when deleting posts."""
        loop = get_event_loop()
        bucket = storage.bucket(app=self._app)
        blob = await loop.run_in_executor(None, bucket.get_blob, blob_name)
        if blob:
            await loop.run_in_executor(None, blob.make_private)

    async def make_image_public(self, blob_name: str):
        """Make the image public. Used when restoring deleted posts."""
        loop = get_event_loop()
        bucket = await loop.run_in_executor(None, functools.partial(storage.bucket, app=self._app))
        blob = await loop.run_in_executor(None, bucket.get_blob, blob_name)
        if blob:
            await loop.run_in_executor(None, blob.make_public)

    async def delete_image(self, blob_name: str):
        """Delete the given image."""
        loop = get_event_loop()
        bucket = await loop.run_in_executor(None, functools.partial(storage.bucket, app=self._app))
        blob = await loop.run_in_executor(None, bucket.get_blob, blob_name)
        if blob:
            await loop.run_in_executor(None, blob.delete)

    async def delete_user_images(self, user_uid: str):
        """Delete the given user's images."""
        loop = get_event_loop()
        bucket = await self._get_bucket(loop)
        image_folder = f"images/{user_uid}"
        get_images_function_sync = functools.partial(bucket.list_blobs, prefix=image_folder)
        blobs = await loop.run_in_executor(None, get_images_function_sync)
        for blob in blobs:
            await loop.run_in_executor(None, blob.delete)

    async def _get_bucket(self, loop) -> Bucket:
        return await loop.run_in_executor(None, functools.partial(storage.bucket, app=self._app))


@dataclass
class FirebaseUser:
    shared_firebase: FirebaseAdminProtocol
    uid: str


_firebase = FirebaseAdmin()


async def get_firebase_user(
    authorization: Optional[str] = Header(None),
) -> FirebaseUser:
    uid = await _firebase.get_uid_from_auth_header(authorization)
    if uid is None:
        raise HTTPException(401, "Not authenticated")
    return FirebaseUser(shared_firebase=_firebase, uid=uid)
