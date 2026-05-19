# User related endpoints

from ouichat_backend.utils.logger import logger
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

    user_doc = await db.get_user(username)
    if user_doc is None:
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR, "Something went wrong trying to fetch connected user"
        )

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

    user_doc = await db.get_user(target_user)
    if not user_doc:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, "Target user not existent on this server"
        )

    logger.info(f"Got target user profile card - username: {username}")

    return GenericItemResponse(
        item=user_doc.model_dump(exclude={"preferences"})
    )


@router.get(
    "/list",
    status_code=status.HTTP_200_OK
)
async def list_all_user_profiles(
    username: str = Depends(decode_sub_access_token)
) -> GenericItemsResponse:
    logger.debug(f"Getting user profile cards - username: {username}")

    user_docs = await db.get_all_users(
        filter={},
        sort={
            "updated_at": -1,
        }
    )

    ret = []

    # Removes all users that have the calling user blacklisted
    for i in range(len(user_docs) - 1, -1, -1):
        if username in user_docs[i].preferences.blacklist:
            user_docs.pop(i)
        else:
            ret.append(
                user_docs[i].model_dump(exclude={"preferences"})
            )

    logger.info(f"Got user profile cards - username: {username}")

    # TODO: Remove blacklist from response
    return GenericItemsResponse(
        items=ret
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
        bl_add=body.who,
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
        bl_del=body.who,
    )
    if update.modified_count == 0:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, "Target user not in blacklist"
        )

    logger.info(f"Expanded current user's blacklist - username: {username}")


@router.post(
    "/profile/status",
    status_code=status.HTTP_200_OK
)
async def change_calling_status(
    body: _bodies.StatusBody,
    username: str = Depends(decode_sub_access_token)
) -> GenericMessageResponse:
    logger.debug(f"Changing current user's status - username: {username} - status: {body.status}")

    message = "Success"
    update = await db.update_user(
        username,
        status=body.status,
    )
    if update.modified_count == 0:
        message = "Unchanged"

    logger.info(f"Chaned current user's status - username: {username}")

    return GenericMessageResponse(
        message=message
    )


@router.post(
    "/profile/picture",
    status_code=status.HTTP_200_OK
)
async def change_calling_profile_picture(
    attachement_id: str, # Maybe allow for `None` value? as a way to remove the picture
    username: str = Depends(decode_sub_access_token)
) -> GenericMessageResponse:
    logger.debug(f"Changing current user's profile pciture - username: {username}")

    message = "Success"
    update = db.update_user(
        username,
        pic_id=attachement_id,
    )
    if update.modified_count == 0:
        message = "Unchanged"

    logger.info(f"Changed current user's profile pciture - username: {username}")

    return GenericMessageResponse(
        message=message
    )