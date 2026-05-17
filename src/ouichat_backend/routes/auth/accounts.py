# User account signing paths

from ouichat_backend.utils.logger import logger
from ouichat_backend.utils.constants import startup
from ouichat_backend.utils.methods import (
    get_password_hash,
    validate_username,
    validate_password,
    timestamp_now,
    db,
)
from ouichat_backend.utils import (
    UserDocument,
    UserPreferencesDocument,
    GenericMessageResponse,
    EndpointTags,
)

from fastapi import (
    APIRouter,
    Response,
    HTTPException,
    Depends,
    status
)
from fastapi.security import OAuth2PasswordRequestForm


router = APIRouter(
    tags=[EndpointTags.AUTHORIZATION]
)


@router.post(
    "/register",
    status_code=status.HTTP_201_CREATED
)
async def register_new_user(
    form_data: OAuth2PasswordRequestForm = Depends(),
) -> GenericMessageResponse:
    """This endpoint attempts to register a new user via a username and password form. If the provided username does not exist in the database, then it is considered valid, but if it already exists, it throws an error.
    
    This endpoint also validates username and password strings to contain only cahracters from a given alphabet. This is an attempt at sterilization."""

    logger.debug(f"Registering new user - username: {form_data.username}")

    # Validate username
    _user_ok, _user_msg = validate_username(form_data.username)
    if not _user_ok:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, _user_msg
        )

    # Check if username exists in db
    one_doc = await db.get_user(form_data.username)
    if one_doc:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "Invalid username"
        )

    # Validate password
    _pass_ok, _pass_msg = validate_password(form_data.password)
    if not _pass_ok:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, _pass_msg
        )
    
    # Add new empty user to db
    new_user = UserDocument(
        username=form_data.username,
        pwd_hash=get_password_hash(form_data.password),
        created_at=timestamp_now(),
        updated_at=timestamp_now(),
    )

    await db.add_user(new_user)

    logger.info(f"Successfully registered new user - username: {form_data.username}")

    return GenericMessageResponse(
        message="Success"
    )