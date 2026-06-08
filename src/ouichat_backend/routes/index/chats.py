# Chat related endpoints

from ouichat_backend.utils.logger import logger
from ouichat_backend.utils import (
    ChatId,
    ConversationDocument,
    ConversationParticipantDocument,
    ConversationPreferencesDocument,
    ConversationProfileDocument,
    GenericItemsResponse,
    GenericMessageResponse,
    GenericItemResponse,
    EndpointTags,
    EndpointPrefixes,
)
from ouichat_backend.utils.methods import (
    decode_sub_access_token,
    timestamp_now,
    db,
)

from . import _bodies, _valids

from fastapi import APIRouter, Depends, HTTPException, status
from typing import Literal
from pydantic import ValidationError

import uuid


router = APIRouter(
    prefix=EndpointPrefixes.CHATS.value,
    tags=[EndpointTags.CHATS]
)


@router.post(
    "/create",
    status_code=status.HTTP_201_CREATED
)
async def create_new_conversation(
    body: _bodies.NewChatBody,
    username: str = Depends(decode_sub_access_token),
) -> GenericItemResponse:
    """Use this endpoint to create a new conversation. Request must provide information such as the type of conversation, the list of participants and wether any participant is an admin, and additional display information for groups.
    
    Args:
    * `body`: `NewChatBody`
    
    Returns:
    * `GenericItemResponse`: A dictionary containing the id of the newly created conversation
    
    Throws:
    * `400`: Current user is not in participant list"""

    chat_id = f"{body.type}_{uuid.uuid4()}"

    logger.debug(f"Creating new conversation - username: {username} - type: {body.type} - chat_id: {chat_id}")

    # Check if calling user in chat participants
    if username not in body.participants.keys():
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "Calling user must be a participant to the conversation"
        )

    # Solve chat participants
    participants = []

    for user, is_admin in body.participants.items():
        participants.append(
            ConversationParticipantDocument(
                username=user,
                is_admin=True if body.type == "direct" or user == username else is_admin,
                last_seen=None
            )
        )
    
    # Solve chat creators and profile
    creators = []
    chat_profile = ConversationProfileDocument()

    if body.type == "direct":
        creators = list(body.participants.keys())
    elif body.type == "group":
        creators = [username]

        # Solve chat profile
        chat_profile = ConversationProfileDocument(
            name=body.group.name,
            description=body.group.description,
            picture_id=body.group.picture_id,
        )

    # Add new chat entry to db
    await db.add_chat(
        ConversationDocument(
            conversation_id=chat_id,
            type=body.type,
            profile=chat_profile,
            preferences=ConversationPreferencesDocument(
                participants=participants,
                created_by=creators,
            ),
            created_at=timestamp_now(),
            updated_at=timestamp_now(),
        )
    )

    logger.info(f"Created new chat - username: {username} - type: {body.type} - chat_id: {chat_id}")

    return GenericItemResponse(
        item={
            "conversation_id": chat_id,
        }
    )


@router.get(
    "/list",
    status_code=status.HTTP_200_OK
)
async def list_all_chats(
    username: str = Depends(decode_sub_access_token),
) -> GenericItemsResponse:
    """Use this endpoint to get a list of all conversations the current user is a participant of.
    
    Returns:
    * `GenericItemsResponse`: A dictionary containing a list of objects with information for each conversation"""

    logger.debug(f"Fetching all chats for user - username: {username}")

    chat_docs = await db.get_all_chats(
        filter={
            "preferences.participants.username": username
        },
        sort={
            "updated_at": -1,
        }
    )

    logger.info(f"Got all chats for user - username: {username} - chats: {len(chat_docs)}")

    return GenericItemsResponse(
        items=chat_docs
    )


@router.get(
    "/chat",
    status_code=status.HTTP_200_OK
)
async def get_chat_details(
    chat_id: ChatId = Depends(_valids.validate_chat_id),
    username: str = Depends(decode_sub_access_token)
):
    """Use this endpoint to get the details about a specific conversation by id. Only searches for conversations the current user is a member of.
    
    Args:
    * `chat_id`: The id of the conversation to fetch details for
    
    Returns:
    * `GenericItemResponse`: A dictionary containing details about the target conversation
    
    Throws:
    * `404`: No conversation with this id exists *or* the current user is not a member of the given conversation."""

    logger.debug(f"Fetching chat details - username: {username} - conversation_id: {chat_id}")

    chat_doc = await db.get_chat(str(chat_id)) # Use chat_id.id and change the create method to return the str(chat_id)
    if not chat_doc:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, "Chat id not found"
        )
    
    user_in_chat = False
    for participant in chat_doc.preferences.participants:
        if participant.username == username:
            user_in_chat = True
            break
    
    if not user_in_chat:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, "User not a participant of this chat"
        )
    
    logger.info(f"Fetched chat details - username: {username} - conversation_id: {chat_id}")

    return GenericItemResponse(
        item=chat_doc
    )


def _get_participant_flags(
    username: str,
    chat_doc: ConversationDocument
) -> dict:
    ret = {
        "owner": False,
        "admin": False,
        "participant": False
    }

    if username in chat_doc.preferences.created_by:
        ret["owner"] = True
        ret["admin"] = True
        ret["participant"] = True
        return ret
    
    for user in chat_doc.preferences.participants:
        if user.username == username:
            ret["participant"] = True
            ret["admin"] = user.is_admin
            return ret

    return ret


@router.post(
    "/participant/admin",
    status_code=status.HTTP_201_CREATED
)
async def set_admin_status(
    body: _bodies.AdminStateBody,
    chat_id: ChatId = Depends(_valids.validate_chat_id),
    username: str = Depends(decode_sub_access_token)
) -> GenericMessageResponse:
    """Use this endpoint to modify the admin states of participants from a given conversation. The current user must be an admin for this action to work.
    
    When using this endpoint the following rules are being followed:
    - Admins *cannot* remove the admin state from other admins, unless they are the creator of the conversation.
    - Admins *can* remove the admin state from themselves, unless they are the creator of the conversation.
    
    Any invalid username will be ignored without throwing an error. This endpoint automatically fails if a direct chat is being targeted.
    
    Args:
    * `chat_id`: The id of the conversation
    * `body`: `AdminStateBody`
    
    Returns:
    * `GenericMessageResponse`: A message detailing the result of the operation
    
    Throws:
    * `404`: Conversation does not exist
    * `405`: Target cconversation is direct *or* current user is not a participant to the conversation *or* current user is not an admin in the conversation"""

    logger.debug(f"Updating admin states - username: {username} - chat_id: {str(chat_id)}")

    if chat_id.type == "direct":
        raise HTTPException(
            405, "Not allowed for `direct` conversations"
        )
    
    # Check if conversation exists in db
    chat_doc = await db.get_chat(str(chat_id)) # Use chat_id.id and change the create method to return the str(chat_id)
    if not chat_doc:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, "Chat id not found"
        )
    
    # Check if current user is a participant and is admin
    flags = _get_participant_flags(username, chat_doc)
    if not flags.get("participant"):
        raise HTTPException(
            405, "User is not a participant in this conversation"
        )
    if not flags.get("admin"):
        raise HTTPException(
            405, "Only admins can alter conversation data"
        )
    
    logger.debug(f"Admins dict: {body.admins}")
    
    # Remove yourself from targets
    body.admins.pop(username, None)

    # Solve other targets depending on owner state
    if not flags.get("owner"):
        for user in chat_doc.preferences.participants:
            if user.is_admin:
                body.admins.pop(user.username, None)
    
    logger.debug(f"Admins dict: {body.admins}")

    # Change admin states
    message = "Success"
    update = await db.update_chat(
        str(chat_id),
        notify=[part.username for part in chat_doc.preferences.participants],
        admins=body.admins
    )
    if update.modified_count == 0:
        message = "Unchanged"

    logger.info(f"Updated admin states - username: {username} - chat_id: {str(chat_id)}")

    return GenericMessageResponse(
        message=message
    )


@router.post(
    "/participant/add",
    status_code=status.HTTP_201_CREATED
)
async def add_user_to_chat(
    body: _bodies.ParticipantInviteBody,
    chat_id: ChatId = Depends(_valids.validate_chat_id),
    username: str = Depends(decode_sub_access_token)
) -> GenericMessageResponse:
    """Use this endpoint to add new users to the target conversation. Current user must be an admin for this action to work. Operation automatically fails on direct conversations.
    
    Args:
    * `chat_id`: The id of the conversation
    * `body`: `ParticipantInviteBody`
    
    Returns:
    * `GenericMessageResponse`: A message detailing the result of the operation
    
    Throws:
    * `400`: Target user is already a participant
    * `404`: Chat not existent *or* target user not existent on the server
    * `405`: Target cconversation is direct *or* current user is not a participant to the conversation *or* current user is not an admin in the conversation"""

    logger.debug(f"Adding users to conversation - username: {username} - chat_id: {str(chat_id)} - count: {len(body.who)}")

    if chat_id.type == "direct":
        raise HTTPException(
            405, "Not allowed for `direct` conversations"
        )

    # Check if conversation exists in db
    chat_doc = await db.get_chat(str(chat_id)) # Use chat_id.id and change the create method to return the str(chat_id)
    if not chat_doc:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, "Chat id not found"
        )
    
    # Check if current user is a participant and is admin
    flags = _get_participant_flags(username, chat_doc)
    if not flags.get("participant"):
        raise HTTPException(
            405, "User is not a participant in this conversation"
        )
    if not flags.get("admin"):
        raise HTTPException(
            405, "Only admins can alter conversation data"
        )
    
    # Ensure users in list exist and are not part of the conversation
    user_docs = await db.get_all_users({})
    server_users = [user.username for user in user_docs]
    chat_participants = [part.username for part in chat_doc.preferences.participants]

    for to_add in body.who:
        if to_add not in server_users:
            raise HTTPException(
                status.HTTP_404_NOT_FOUND, f"User `{to_add}` not existent on this server"
            )
        if to_add in chat_participants:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST, f"User `{to_add}` is already a participant in this conversation"
            )
        
    # Add users
    message = "Success"
    update = await db.update_chat(
        str(chat_id),
        notify=[*chat_participants, body.who],
        to_add=body.who
    )
    if update.modified_count == 0:
        message = "Unchanged"

    logger.info(f"Added users to conversation - username: {username} - chat_id: {str(chat_id)} - count: {len(body.who)}")

    return GenericMessageResponse(
        message=message
    )


@router.delete(
    "/participant/remove",
    status_code=status.HTTP_204_NO_CONTENT
)
async def remove_user_from_chat(
    body: _bodies.ParticipantInviteBody,
    chat_id: ChatId = Depends(_valids.validate_chat_id),
    username: str = Depends(decode_sub_access_token)
):
    """Use this endpoint to remove users from the target conversation. Current user must be an admin for this action to work. Operation automatically fails on direct conversations.

    When using this endpoint the following rules are being followed:
    - Admins *cannot* remove another admin from the conversation, unless they are the creator of the conversation.
    - Admins *cannot* remove themselves from the conversation, as that operation has its dedicated endpoint.
    
    Args:
    * `chat_id`: The id of the conversation
    * `body`: `ParticipantInviteBody`
    
    Throws:
    * `404`: Chat not existent *or* target user is not a participant of the conversartion
    * `405`: Target cconversation is direct *or* current user is not a participant to the conversation *or* current user is not an admin in the conversation"""

    logger.debug(f"Removing users fome the conversation - username: {username} - chat_id: {str(chat_id)} - count: {len(body.who)}")

    if chat_id.type == "direct":
        raise HTTPException(
            405, "Not allowed for `direct` conversations"
        )

    # Check if conversation exists in db
    chat_doc = await db.get_chat(str(chat_id)) # Use chat_id.id and change the create method to return the str(chat_id)
    if not chat_doc:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, "Chat id not found"
        )
    
    # Check if current user is a participant and is admin
    flags = _get_participant_flags(username, chat_doc)
    if not flags.get("participant"):
        raise HTTPException(
            405, "User is not a participant in this conversation"
        )
    if not flags.get("admin"):
        raise HTTPException(
            405, "Only admins can alter conversation data"
        )
    
    # Remove yourself from targets
    try:
        body.who.remove(username)
    except ValueError:
        pass

    # Ensure users are part of the conversation
    chat_participants = {
        part.username: part.is_admin for part in chat_doc.preferences.participants
    }
    logger.debug(f"Participants: {chat_participants}")

    to_remove = []
    for to_rm in body.who:
        if to_rm not in list(chat_participants.keys()):
            raise HTTPException(
                status.HTTP_404_NOT_FOUND, f"User `{to_rm}` not a participant in the conversation"
            )
        if not flags.get("owner") and chat_participants.get(to_rm):
            continue
        to_remove.append(to_rm)
    logger.debug(f"To remove: {to_remove}")
        
    # Remove users
    await db.update_chat(
        str(chat_id),
        notify=[part.username for part in chat_doc.preferences.participants],
        to_remove=to_remove
    )

    logger.info(f"Removing users fome the conversation - username: {username} - chat_id: {str(chat_id)} - count: {len(to_remove)}")


@router.delete(
    "/participant/leave",
    status_code=status.HTTP_204_NO_CONTENT
)
async def leave_chat(
    chat_id: ChatId = Depends(_valids.validate_chat_id),
    username: str = Depends(decode_sub_access_token)
):
    """Use this endpoint to remove the current user from the participant list for the target conversation. If the current user is the creator of the conversation, the chat gets deleted. This operation fails for direct conversations.
    
    Args:
    * `chat_id`: The id of the conversation
    
    Throws:
    * `404`: Conversation not existent
    * `405`: Chat id references direct conversation"""

    logger.debug(f"Attempting to leave chat - chat_id: {str(chat_id)} - username: {username}")

    if chat_id.type == "direct":
        raise HTTPException(
            405, "Not allowed for `direct` conversations"
        )
    
    # Check if conversation exists in db
    chat_doc = await db.get_chat(str(chat_id)) # Use chat_id.id and change the create method to return the str(chat_id)
    if not chat_doc:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, "Chat id not found"
        )
    
    # Check if current user is a participant and is admin
    flags = _get_participant_flags(username, chat_doc)
    if not flags.get("participant"):
        raise HTTPException(
            405, "User is not a participant in this conversation"
        )
    
    chat_participants = [part.username for part in chat_doc.preferences.participants]
    
    # Either update participant list or delete chat
    if flags.get("owner"):
        await db.delete_chat(
            str(chat_id),
            notify=chat_participants
        )

        logger.debug(f"Owner left. Deleted chat - chat_id: {str(chat_id)} - username: {username}")
    else:
        await db.update_chat(
            str(chat_id),
            notify=chat_participants,
            to_remove=[username]
        )

    logger.info(f"Left chat - chat_id: {str(chat_id)} - username: {username}")


@router.post(
    "/preferences/name",
    status_code=status.HTTP_200_OK
)
async def update_chat_name(
    body: _bodies.NameBody,
    chat_id: ChatId = Depends(_valids.validate_chat_id),
    username: str = Depends(decode_sub_access_token)
) -> GenericMessageResponse:
    """Use this endpoint to change the display name of a conversation. Current user must be an admin for this operation to succeed. Operation fails for direct conversations.
    
    Args:
    * `chat_id`: The id of the conversation
    * `body`: `NameBody`
    
    Returns:
    * `GenericMessageResponse`: A message detailing the result of the conversation
    
    Throws:
    * `405`: Conversation is direct *or* current user is not a participant of the conversation *or* current user is not an admin"""

    logger.debug(f"Updating conversation name - chat_id: {str(chat_id)} - username: {username}")

    if chat_id.type == "direct":
        raise HTTPException(
            405, "Not allowed for `direct` conversations"
        )

    # Check if current user is a participant and is admin
    flags = _get_participant_flags(username, chat_doc)
    if not flags.get("participant"):
        raise HTTPException(
            405, "User is not a participant in this conversation"
        )
    if not flags.get("admin"):
        raise HTTPException(
            405, "Only admins can alter conversation data"
        )

    message = "Success"
    update = await db.update_chat(
        str(chat_id),
        notify=[part.username for part in chat_doc.preferences.participants],
        name=body.name
    )
    if update.modified_count == 0:
        message = "Unchanged"

    logger.info(f"Updated conversation name - chat_id: {str(chat_id)} - username: {username}")

    return GenericMessageResponse(
        message=message
    )


@router.post(
    "/preferences/description",
    status_code=status.HTTP_200_OK
)
async def update_chat_description(
    body: _bodies.DescriptionBody,
    chat_id: ChatId = Depends(_valids.validate_chat_id),
    username: str = Depends(decode_sub_access_token)
):
    """Use this endpoint to change the display description of a conversation. Current user must be an admin for this operation to succeed. Operation fails for direct conversations.
    
    Args:
    * `chat_id`: The id of the conversation
    * `body`: `NameBody`
    
    Returns:
    * `GenericMessageResponse`: A message detailing the result of the conversation
    
    Throws:
    * `405`: Conversation is direct *or* current user is not a participant of the conversation *or* current user is not an admin"""

    logger.debug(f"Updating conversation description - chat_id: {str(chat_id)} - username: {username}")

    if chat_id.type == "direct":
        raise HTTPException(
            405, "Not allowed for `direct` conversations"
        )
    
    # Check if current user is a participant and is admin
    flags = _get_participant_flags(username, chat_doc)
    if not flags.get("participant"):
        raise HTTPException(
            405, "User is not a participant in this conversation"
        )
    if not flags.get("admin"):
        raise HTTPException(
            405, "Only admins can alter conversation data"
        )

    message = "Success"
    update = await db.update_chat(
        str(chat_id),
        notify=[part.username for part in chat_doc.preferences.participants],
        description=body.description
    )
    if update.modified_count == 0:
        message = "Unchanged"

    logger.info(f"Updated conversation description - chat_id: {str(chat_id)} - username: {username}")

    return GenericMessageResponse(
        message=message
    )


@router.post(
    "/preferences/picture",
    status_code=status.HTTP_200_OK
)
async def update_chat_icon(
    body: _bodies.IconBody,
    chat_id: ChatId = Depends(_valids.validate_chat_id),
    username: str = Depends(decode_sub_access_token)
):
    """Use this endpoint to change the display icon of a conversation. Current user must be an admin for this operation to succeed. Operation fails for direct conversations.
    
    Args:
    * `chat_id`: The id of the conversation
    * `body`: `NameBody`
    
    Returns:
    * `GenericMessageResponse`: A message detailing the result of the conversation
    
    Throws:
    * `405`: Conversation is direct *or* current user is not a participant of the conversation *or* current user is not an admin"""

    logger.debug(f"Updating conversation icon - chat_id: {str(chat_id)} - username: {username}")

    if chat_id.type == "direct":
        raise HTTPException(
            405, "Not allowed for `direct` conversations"
        )

    # Check if current user is a participant and is admin
    flags = _get_participant_flags(username, chat_doc)
    if not flags.get("participant"):
        raise HTTPException(
            405, "User is not a participant in this conversation"
        )
    if not flags.get("admin"):
        raise HTTPException(
            405, "Only admins can alter conversation data"
        )

    message = "Success"
    update = await db.update_chat(
        str(chat_id),
        notify=[part.username for part in chat_doc.preferences.participants],
        icon_id=body.icon_id
    )
    if update.modified_count == 0:
        message = "Unchanged"

    logger.info(f"Updated conversation icon - chat_id: {str(chat_id)} - username: {username}")

    return GenericMessageResponse(
        message=message
    )