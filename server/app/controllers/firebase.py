import uuid
from dataclasses import dataclass
from typing import Optional, IO, Tuple, Protocol

import firebase_admin
from fastapi import Header, HTTPException
from firebase_admin import auth, storage
from firebase_admin.auth import InvalidIdTokenError, ExpiredIdTokenError, RevokedIdTokenError, CertificateFetchError, \
    UserNotFoundError
from firebase_admin.exceptions import FirebaseError
from google.cloud.exceptions import GoogleCloudError

from app.models import models


class FirebaseAdminProtocol(Protocol):
    def get_uid_from_token(self, id_token: str) -> Optional[str]: ...

    def get_phone_number_from_uid(self, uid: str) -> str: ...

    def get_uid_from_auth_header(self, authorization: str) -> Optional[str]: ...

    def upload_image(self, user: models.User, image_id: str, file_obj: IO) -> Optional[Tuple[str, str]]: ...

    def make_image_private(self, blob_name: str): ...

    def delete_image(self, blob_name: str): ...


class FirebaseAdmin:
    def __init__(self):
        self._app = firebase_admin.initialize_app(options={
            "storageBucket": "goodplaces-app.appspot.com"
        })

    def get_uid_from_token(self, id_token: str) -> Optional[str]:
        """Get the user's uid from the given Firebase id token."""
        try:
            decoded_token = auth.verify_id_token(id_token, app=self._app, check_revoked=True)
            return decoded_token.get("uid")
        except (ValueError, InvalidIdTokenError, ExpiredIdTokenError, RevokedIdTokenError, CertificateFetchError):
            return None
        except Exception as e:
            print("Unexpected exception:", e)
            return None

    def get_phone_number_from_uid(self, uid: str) -> Optional[str]:
        try:
            firebase_user = auth.get_user(uid, app=self._app)
            return firebase_user.phone_number
        except (ValueError, UserNotFoundError, FirebaseError):
            return None

    def get_uid_from_auth_header(self, authorization: str) -> Optional[str]:
        """Get the user's uid from the given authorization header."""
        if authorization is None or not authorization.startswith("Bearer "):
            return None
        id_token = authorization[7:]
        return self.get_uid_from_token(id_token)

    # Storage
    def upload_image(self, user: models.User, image_id: str, file_obj: IO) -> Optional[Tuple[str, str]]:
        """Upload the given image to Firebase, returning the blob name and public URL if uploading was successful."""
        bucket = storage.bucket(app=self._app)
        blob = bucket.blob(f"images/{user.uid}/{image_id}.jpg")
        # Known issue in firebase, this metadata is necessary to view images via Firebase console
        blob.metadata = {
            "firebaseStorageDownloadTokens": uuid.uuid4()
        }
        try:
            blob.upload_from_file(file_obj, content_type="image/jpeg")
        except GoogleCloudError as e:
            print("Failed to upload image", e)
            return None
        blob.make_public()
        return blob.name, blob.public_url

    def make_image_private(self, blob_name: str):
        """Revoke read access for anonymous users. Used when deleting posts."""
        bucket = storage.bucket(app=self._app)
        blob = bucket.get_blob(blob_name)
        if blob:
            blob.make_private()

    def delete_image(self, blob_name: str):
        """Delete the given image."""
        bucket = storage.bucket(app=self._app)
        blob = bucket.get_blob(blob_name)
        if blob:
            blob.delete()


@dataclass
class FirebaseUser:
    shared_firebase: FirebaseAdminProtocol
    uid: str


_firebase = FirebaseAdmin()


def get_firebase_user(authorization: Optional[str] = Header(None)) -> FirebaseUser:
    uid = _firebase.get_uid_from_auth_header(authorization)
    if uid is None:
        raise HTTPException(401, "Not authenticated")
    return FirebaseUser(shared_firebase=_firebase, uid=uid)
