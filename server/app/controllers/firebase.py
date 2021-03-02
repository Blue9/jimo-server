import uuid
from typing import Optional, IO, Tuple

import firebase_admin
from firebase_admin import auth, storage
from firebase_admin.auth import InvalidIdTokenError, ExpiredIdTokenError, RevokedIdTokenError, CertificateFetchError, \
    UserNotFoundError, UserRecord
from firebase_admin.exceptions import FirebaseError
from google.cloud.exceptions import GoogleCloudError

from app import config
from app.models import models

_app = firebase_admin.initialize_app(options={
    "storageBucket": "goodplaces-app.appspot.com"
})


def get_uid_from_token(id_token: str) -> Optional[str]:
    """Get the user's uid from the given Firebase id token."""
    # TODO(gmekkat): remove in production
    test_token = "test"
    test_uid = "test"
    if id_token == test_token:
        return test_uid
    try:
        decoded_token = auth.verify_id_token(id_token, check_revoked=True)
        return decoded_token.get("uid")
    except (InvalidIdTokenError, ExpiredIdTokenError, RevokedIdTokenError, CertificateFetchError) as e:
        return None


def get_phone_number_from_uid(uid: str) -> Optional[str]:
    try:
        firebase_user = auth.get_user(uid)
        return firebase_user.phone_number
    except (ValueError, UserNotFoundError, FirebaseError):
        return None


def get_uid_from_auth_header(authorization: str) -> Optional[str]:
    """Get the user's uid from the given authorization header."""
    if authorization is None or not authorization.startswith("Bearer "):
        return None
    id_token = authorization[7:]
    return get_uid_from_token(id_token)


def get_test_token(uid: str) -> Optional[str]:
    """Generate and return a Firebase id token for the given uid."""
    from urllib.parse import urlencode
    from urllib.request import Request, urlopen
    import json
    custom_token = auth.create_custom_token(uid).decode("utf-8")
    url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithCustomToken?key={config.FIREBASE_API_KEY}"
    fields = dict(token=custom_token, returnSecureToken=True)
    request = Request(url, urlencode(fields).encode())
    response = urlopen(request).read().decode()
    return json.loads(response).get("idToken")


def get_uid_from_phone_number(phone_number: str) -> Optional[str]:
    try:
        user: UserRecord = auth.get_user_by_phone_number(phone_number)
        return user.uid
    except (ValueError, UserNotFoundError, FirebaseError):
        return None


# Storage
def upload_image(user: models.User, image_id: str, file_obj: IO) -> Optional[Tuple[str, str]]:
    """Upload the given image to Firebase, returning the blob name and public URL if uploading was successful."""
    bucket = storage.bucket()
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


def make_image_private(blob_name: str):
    """Revoke read access for anonymous users. Used when deleting posts."""
    bucket = storage.bucket()
    blob = bucket.get_blob(blob_name)
    if blob:
        blob.make_private()
