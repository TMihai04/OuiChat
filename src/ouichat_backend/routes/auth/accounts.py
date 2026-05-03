# User account signing paths

from ouichat_backend.logger import logger
from ouichat_backend.utils.constants import startup
from ouichat_backend.utils.methods import (
    get_acollection,
    get_password_hash,
    validate_username,
    validate_password,
    get_users_collection,
)
from ouichat_backend.utils import (
    UserDocument,
    UserPreferencesDocument,
    GenericResponse,
)

from fastapi import (
    APIRouter,
    Response,
    HTTPException,
    Depends,
)
from fastapi.security import OAuth2PasswordRequestForm
from datetime import datetime, timezone


router = APIRouter()


@router.post("/register")
async def register_new_user(
    form_data: OAuth2PasswordRequestForm = Depends(),
) -> GenericResponse:
    """This endpoint attempts to register a new user via a username and password form. If the provided username does not exist in the database, then it is considered valid, but if it already exists, it throws an error.
    
    This endpoint also validates username and password strings to contain only cahracters from a given alphabet. This is an attempt at sterilization."""

    logger.debug(f"Registering new user - username: {form_data.username}")

    # Validate username
    _user_ok, _user_msg = validate_username(form_data.username)
    if not _user_ok:
        raise HTTPException(400, _user_msg)

    # Check if username exists in db
    users_collection = get_users_collection()
    one_doc = await users_collection.find_one(
        filter={
            "username": form_data.username,
        }
    )
    if one_doc:
        raise HTTPException(400, "Invalid username")

    # Validate password
    _pass_ok, _pass_msg = validate_password(form_data.password)
    if not _pass_ok:
        raise HTTPException(400, _pass_msg)
    
    # Add new empty user to db
    new_user = UserDocument(
        username=form_data.username,
        pwd_hash=get_password_hash(form_data.password),
        created_at=int(datetime.now(timezone.utc).timestamp() * 1000),
        updated_at=int(datetime.now(timezone.utc).timestamp() * 1000),
    )

    await users_collection.insert_one(new_user.model_dump())

    logger.info(f"Successfully registered new user - username: {form_data.username}")

    return GenericResponse(
        message="Success"
    )