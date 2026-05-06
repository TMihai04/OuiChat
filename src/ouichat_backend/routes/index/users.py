# User related endpoints

from ouichat_backend.logger import logger
from ouichat_backend.utils import (
    UserPreferencesDocument,
    GenericItemsResponse,
    GenericMessageResponse,
    GenericItemResponse,
    EndpointTags,
    EndpointPrefixes,
)
from ouichat_backend.utils.methods import (
    decode_sub_access_token,
    db,
)

from . import _bodies

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status


router = APIRouter(
    prefix=EndpointPrefixes.USERS.value,
    tags=[EndpointTags.USERS]
)


@router.get(
    "/me",
    status_code=status.HTTP_200_OK
)
async def get_calling_user_info(
    username: str = Depends(decode_sub_access_token)
) -> GenericItemResponse:
    logger.debug(f"Getting current user information - username: {username}")

    user_doc = await db.get_user(
        username,
        projection={
            "_id": 0,
            "username": 1,
            "profile": 1,
            "preferences": 1,
            "last_login": 1
        }
    )
    # NOTE: Does `user_doc is None` need to be checked?

    logger.info(f"Got current user information - username: {username}")

    return GenericItemResponse(
        item=user_doc
    )


@router.get(
    "/profile",
    status_code=status.HTTP_200_OK
)
async def get_target_user_profile(
    target_user: str,
    username: str = Depends(decode_sub_access_token)
) -> GenericItemResponse:
    logger.debug(f"Getting target user profile card - username: {username} - target: {target_user}")

    if target_user == username:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "For self query use dedicated endpoint"
        )

    user_doc = await db.get_user(
        target_user,
        projection={
            "_id": 0,
            "username": 1,
            "profile": 1,
            "last_login": 1
        }
    )
    if not user_doc:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, "Target user not existent on this server"
        )

    logger.info(f"Got target user profile card - username: {username}")

    return GenericItemResponse(
        item=user_doc
    )


@router.get(
    "/list",
    status_code=status.HTTP_200_OK
)
async def list_all_user_profiles(
    username: str = Depends(decode_sub_access_token)
) -> GenericItemsResponse:
    logger.debug(f"Getting all user profile cards - username: {username}")

    user_docs = await db.get_all_users(
        projection={
            "_id": 0,
            "username": 1,
            "profile": 1,
            "last_login": 1
        }
    )

    logger.info(f"Got all user profile cards - username: {username}")

    return GenericItemsResponse(
        items=user_docs
    )


@router.post(
    "/preferences/blacklist",
    status_code=status.HTTP_201_CREATED
)
async def add_to_calling_blacklist(
    body: _bodies.BlacklistBody,
    username: str = Depends(decode_sub_access_token)
) -> GenericMessageResponse:
    logger.debug(f"Adding to current user's blacklist - username: {username} - target: {body.who}")

    if body.who == username:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "Cannot blacklist self"
        )
    if not await db.user_exists(body.who):
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, "Target user does not exist"
        )

    message = "Success"
    update = await db.update_user(
        username,
        update={
            "$addToSet": {"preferences.blacklist": body.who}
        }
    )
    if update.modified_count == 0:
        message = "Target already in blacklist"

    logger.info(f"Expanded current user's blacklist - username: {username}")

    return GenericMessageResponse(
        message=message
    )


@router.delete(
    "/preferences/blacklist",
    status_code=status.HTTP_204_NO_CONTENT
)
async def remove_from_calling_blacklist(
    body: _bodies.BlacklistBody,
    username: str = Depends(decode_sub_access_token)
):
    logger.debug(f"Adding to current user's blacklist - username: {username} - target: {body.who}")

    if body.who == username:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "Cannot whitelist self"
        )
    if not await db.user_exists(body.who):
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, "Target user does not exist"
        )

    update = await db.update_user(
        username,
        update={
            "$pull": {"preferences.blacklist": {"$eq": body.who}}
        }
    )
    if update.modified_count == 0:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, "Target user not in blacklist"
        )

    logger.info(f"Expanded current user's blacklist - username: {username}")


@router.post(
    "/preferences/status",
    status_code=status.HTTP_201_CREATED
)
async def change_calling_status(
    body: _bodies.StatusBody,
    username: str = Depends(decode_sub_access_token)
) -> GenericMessageResponse:
    logger.debug(f"Changing current user's status - username: {username} - status: {body.status}")

    update = await db.update_user(
        username,
        update={
            "$set": {"profile.status": body.status}
        }
    )

    logger.info(f"Chaned current user's status - username: {username}")

    return GenericMessageResponse()


@router.post(
    "/preferences/picture",
    status_code=status.HTTP_501_NOT_IMPLEMENTED
)
async def change_calling_profile_picture(
    file: UploadFile,
    username: str = Depends(decode_sub_access_token)
) -> GenericMessageResponse:
    return GenericMessageResponse(
        message="Not implemented"
    )