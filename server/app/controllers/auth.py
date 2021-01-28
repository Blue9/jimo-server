from typing import Optional

import firebase_admin
from firebase_admin import auth
from firebase_admin.auth import InvalidIdTokenError, ExpiredIdTokenError, RevokedIdTokenError, CertificateFetchError

import config
from app.models.models import User, Post

_app = firebase_admin.initialize_app()


def get_uid_from_token(id_token: str) -> Optional[str]:
    """Get the user's uid from the given Firebase id token."""
    # TODO(gmekkat): remove in production
    test_token = "test"
    test_uid = "k4EZgOr5UJgpwMkIb3WmOMv9dKu1"
    if id_token == test_token:
        return test_uid
    try:
        decoded_token = auth.verify_id_token(id_token, check_revoked=True)
        return decoded_token.get("uid")
    except (InvalidIdTokenError, ExpiredIdTokenError, RevokedIdTokenError, CertificateFetchError) as e:
        print("error with", e)
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


def user_can_view_post(user: User, post: Post) -> bool:
    """Return whether the user is authorized to view the given post or not."""
    return not post.user.private_account or post.user in user.following
