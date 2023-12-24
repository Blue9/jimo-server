from typing_extensions import Annotated
from pydantic import AfterValidator
from app.features.users import validators

ValidatedUsername = Annotated[str, AfterValidator(validators.validate_username)]
ValidatedName = Annotated[str, AfterValidator(validators.validate_name)]
