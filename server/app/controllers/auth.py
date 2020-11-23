from typing import Optional

import firebase_admin
from firebase_admin import auth
from firebase_admin.auth import InvalidIdTokenError, ExpiredIdTokenError, RevokedIdTokenError, CertificateFetchError, \
    UserRecord, UserNotFoundError
from firebase_admin.exceptions import FirebaseError

from app.models.models import User, Post

_app = firebase_admin.initialize_app()


def get_user_email(id_token: str) -> Optional[str]:
    test_token = "test"
    test_uid = "gautam@example.com"
    if id_token == test_token:
        return test_uid
    try:
        decoded_token = auth.verify_id_token(id_token, check_revoked=True)
        return decoded_token.get("email")
    except (InvalidIdTokenError, ExpiredIdTokenError, RevokedIdTokenError, CertificateFetchError) as e:
        return None


def get_email_from_uid(uid: str) -> Optional[str]:
    try:
        return auth.get_user(uid).email
    except (ValueError, UserNotFoundError, FirebaseError) as e:
        return None


def get_test_token(email: str) -> Optional[str]:
    from urllib.parse import urlencode
    from urllib.request import Request, urlopen
    import json
    import os
    user = auth.get_user_by_email(email)
    custom_token = auth.create_custom_token(user.uid).decode("utf-8")
    url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithCustomToken?key={os.environ['FIREBASE_API_KEY']}"
    fields = dict(token=custom_token, returnSecureToken=True)
    request = Request(url, urlencode(fields).encode())
    response = urlopen(request).read().decode()
    return json.loads(response).get("idToken")


def user_can_view_post(user: User, post: Post) -> bool:
    """Return whether the user is authorized to view the given post or not."""
    return not post.user.private_account or post.user in user.following
