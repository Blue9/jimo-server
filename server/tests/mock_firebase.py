from typing import Optional, IO, Tuple

from app.models import models


class MockFirebaseAdmin:
    def __init__(self):
        pass

    def get_uid_from_token(self, id_token: str) -> Optional[str]:
        return None

    def get_phone_number_from_uid(self, uid: str) -> Optional[str]:
        return None

    def get_uid_from_auth_header(self, authorization: str) -> Optional[str]:
        return None

    def upload_image(self, user: models.User, image_id: str, file_obj: IO) -> Optional[Tuple[str, str]]:
        return None

    def make_image_private(self, blob_name: str):
        pass

    def make_image_public(self, blob_name: str):
        pass

    def delete_image(self, blob_name: str):
        pass
