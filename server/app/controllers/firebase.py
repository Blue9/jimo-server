from typing import Optional

import firebase_admin
from firebase_admin import auth
from firebase_admin.auth import InvalidIdTokenError, ExpiredIdTokenError, RevokedIdTokenError, CertificateFetchError, \
    UserNotFoundError, UserRecord
from firebase_admin.exceptions import FirebaseError

from app import config

_app = firebase_admin.initialize_app()


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
    firebase_user = auth.get_user(uid)
    return firebase_user.phone_number


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
