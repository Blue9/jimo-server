import uuid
from typing import Optional, IO, Tuple

from app.controllers.firebase import FirebaseAdminProtocol


class MockFirebaseAdmin(FirebaseAdminProtocol):
    def __init__(self):
        pass

    def get_uid_from_token(self, id_token: str) -> Optional[str]:
        return None

    def get_phone_number_from_uid(self, uid: str) -> Optional[str]:
        return None

    def get_uid_from_auth_header(self, authorization: Optional[str]) -> Optional[str]:
        return None

    def upload_image(self, user_uid: str, image_id: uuid.UUID, file_obj: IO) -> Optional[Tuple[str, str]]:
        return None

    def make_image_private(self, blob_name: str):
        pass

    def make_image_public(self, blob_name: str):
        pass

    def delete_image(self, blob_name: str):
        pass
