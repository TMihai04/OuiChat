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
    """Use this endpoint to receive information about the current user.
    
    Returns:
    * `GenericItemResponse`: A dictionary containing the user information"""

    logger.debug(f"Getting current user information - username: {username}")

    user_doc = await db.get_user(username)
    if user_doc is None:
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR, "Something went wrong trying to fetch connected user"
        )

    logger.info(f"Got current user information - username: {username}")

    return GenericItemResponse(
        item=user_doc.model_dump(exclude={"pwd_hash"})
    )


@router.get(
    "/profile",
    status_code=status.HTTP_200_OK
)
async def get_target_user_profile(
    target_user: str,
    username: str = Depends(decode_sub_access_token)
) -> GenericItemResponse:
    """Use this endpoint to receive information about a specific user.
    
    Args:
    * `target_user`: The username of the desired user
    
    Returns:
    * `GenericItemResponse`: A dictionary containing information about the target user
    
    Throws:
    * `400`: Target user is the same as the current user
    * `404`: Target user does not exist"""

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
        item=user_doc.model_dump(exclude={"pwd_hash", "preferences"})
    )


@router.get(
    "/list",
    status_code=status.HTTP_200_OK
)
async def list_all_user_profiles(
    username: str = Depends(decode_sub_access_token)
) -> GenericItemResponse:
    """Use this endpoint for information on all users from the server. Users will be separated in two lists based on wether they are currently blacklisting the current user.
    
    Returns:
    * `GenericItemResponse`: A dictionary containing lists of user information. The two keys used for the lists are 'white' and 'black'"""
    
    logger.debug(f"Getting user profile cards - username: {username}")

    user_docs = await db.get_all_users(
        filter={},
        sort={
            "updated_at": -1,
        }
    )

    ret = {
        "white": [],
        "black": []
    }

    # Removes all users that have the calling user blacklisted
    for user in user_docs:
        field = "white"
        if username in user.preferences.blacklist:
            field = "black"
        ret[field].append(user.model_dump(exclude={"preferences", "pwd_hash"}))

    logger.info(f"Got user profile cards - username: {username}")

    return GenericItemResponse(
        item=ret
    )


@router.post(
    "/preferences/blacklist",
    status_code=status.HTTP_201_CREATED
)
async def add_to_calling_blacklist(
    body: _bodies.BlacklistBody,
    username: str = Depends(decode_sub_access_token)
) -> GenericMessageResponse:
    """Use this endpoint to 'block' a user. This adds the target user to the current user's blacklist
    
    Args:
    * `body`: `BlacklistBody`
    
    Returns:
    * `GenericMessageResponse`: Message detailing operation result
    
    Throws:
    * `400`: Target user is equal to current user
    * `404`: Target user does not exist"""

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
    """Use this endpoint to 'unblock' a user. This removes the target user from the current user's blacklist
    
    Args:
    * `body`: `BlacklistBody`
    
    Returns:
    * `GenericMessageResponse`: Message detailing operation result
    
    Throws:
    * `400`: Target user is equal to current user
    * `404`: Target user does not exist on either the server or in the blacklist"""

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
    "/preferences/muted",
    status_code=status.HTTP_201_CREATED
)
async def add_to_calling_muted(
    body: _bodies.MuteChatBody,
    username: str = Depends(decode_sub_access_token)
) -> GenericMessageResponse:
    """Use this endpoint to mute notifications for a chat.
    
    Args:
    * `body`: `MuteChatBody`
    
    Returns:
    * `GenericMessageResponse`: Message detailing operation result
    
    Throws:
    * `404`: Target chat does not exist
    * `403`: Calling user is not a participant in the target chat"""

    logger.debug(f"Muting chat for current user - username: {username} - chat_id: {body.chat_id}")

    chat_doc = await db.get_chat(body.chat_id)
    if chat_doc is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, "Target chat does not exist"
        )
    
    if not any(part.username == username for part in chat_doc.preferences.participants):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "Calling user is not a participant in target chat"
        )

    message = "Success"
    update = await db.update_user(
        username,
        mute_add=body.chat_id,
    )
    if update.modified_count == 0:
        message = "Chat already muted"

    logger.info(f"Muted chat for user - username: {username} - chat_id: {body.chat_id}")

    return GenericMessageResponse(
        message=message
    )


@router.delete(
    "/preferences/muted",
    status_code=status.HTTP_204_NO_CONTENT
)
async def remove_from_calling_muted(
    body: _bodies.MuteChatBody,
    username: str = Depends(decode_sub_access_token)
):
    """Use this endpoint to unmute notifications for a chat.
    
    Args:
    * `body`: `MuteChatBody`
    
    Returns:
    * `204 No Content` on success
    
    Throws:
    * `404`: Chat not in muted list"""

    logger.debug(f"Unmuting chat for current user - username: {username} - chat_id: {body.chat_id}")

    update = await db.update_user(
        username,
        mute_del=body.chat_id,
    )
    if update.modified_count == 0:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, "Chat not in muted list"
        )

    logger.info(f"Unmuted chat for user - username: {username} - chat_id: {body.chat_id}")


@router.post(
    "/profile/status",
    status_code=status.HTTP_200_OK
)
async def change_calling_status(
    body: _bodies.StatusBody,
    username: str = Depends(decode_sub_access_token)
) -> GenericMessageResponse:
    """Use this endpoint to change the current user's profile status.
    
    Args:
    * `body`: `StatusBody`
    
    Returns:
    * `GenericMessageResponse`: Message detailing operation result"""

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
    body: _bodies.IconBody,
    username: str = Depends(decode_sub_access_token)
) -> GenericMessageResponse:
    """Use this endpoint to change the current user's profile icon.
    
    Args:
    * `body`: `IconBody`
    
    Returns:
    * `GenericMessageResponse`: Message detailing operation result"""

    logger.debug(f"Changing current user's profile pciture - username: {username}")

    message = "Success"
    update = await db.update_user(
        username,
        pic_id=body.icon_id,
    )
    if update.modified_count == 0:
        message = "Unchanged"

    logger.info(f"Changed current user's profile pciture - username: {username}")

    return GenericMessageResponse(
        message=message
    )