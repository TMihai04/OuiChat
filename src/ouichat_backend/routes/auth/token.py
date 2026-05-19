# Authentification endpoints

from ouichat_backend.utils.logger import logger
from ouichat_backend.utils.methods import (
    get_password_hash,
    get_dummy_hash,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
    timestamp_now,
    db,
)
from ouichat_backend.utils import (
    CREDENTIALS_EXCEPTION,
    OAUTH2_SCHEME,
    REFRESH_SCHEME,
    NewTokensResponse,
    EndpointTags,
)

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)
from fastapi.security import (
    OAuth2PasswordRequestFormStrict,
    HTTPAuthorizationCredentials,
)

import jwt
import uuid


router = APIRouter(
    tags=[EndpointTags.AUTHORIZATION]
)


@router.post(
    "/login",
    status_code=status.HTTP_201_CREATED
)
async def login_for_tokens(
    form_data: OAuth2PasswordRequestFormStrict = Depends(),
) -> NewTokensResponse:
    """This endpoint logs in an existent user using a form. A login is requied every time the user's session expires, or whenever the app is first opened on the user's end."""

    logger.debug(f"Logging in user - username: {form_data.username}")

    # Check if user exists
    one_doc = await db.get_user(form_data.username)
    if not one_doc:
        verify_password(form_data.password, get_dummy_hash())
        raise CREDENTIALS_EXCEPTION
    if not verify_password(form_data.password, one_doc.pwd_hash):
        raise CREDENTIALS_EXCEPTION
    
    # Generate new token pair
    refresh_token_id = str(uuid.uuid4())
    
    access_token = create_access_token(form_data.username)
    refresh_token = create_refresh_token(form_data.username, refresh_token_id)

    await db.update_user(
        form_data.username,
        login=timestamp_now(),
    )

    logger.debug(f"access: {access_token}\n\trefresh: {refresh_token}")
    logger.info(f"Successfully logged in and generated keys - username: {form_data.username}")

    return NewTokensResponse(
        access_token=access_token,
        refresh_token=refresh_token,
    )
    

@router.post(
    "/refresh",
    status_code=status.HTTP_201_CREATED
)
async def refresh_for_tokens(
    credentials: HTTPAuthorizationCredentials = Depends(REFRESH_SCHEME),
) -> NewTokensResponse:
    logger.debug(f"Refreshing tokens - oldToken: {credentials.credentials}")

    try:
        payload = decode_token(credentials.credentials)
    except Exception:
        raise CREDENTIALS_EXCEPTION

    if payload.get("type", "") != "refresh":
        raise CREDENTIALS_EXCEPTION
    
    # Generate new token pair
    refresh_token_id = str(uuid.uuid4())
    
    access_token = create_access_token(payload.get("sub"))
    refresh_token = create_refresh_token(payload.get("sub"), refresh_token_id)

    logger.info(f"Successfully refreshed tokens - username: {payload.get("sub")}")

    return NewTokensResponse(
        access_token=access_token,
        refresh_token=refresh_token,
    )

