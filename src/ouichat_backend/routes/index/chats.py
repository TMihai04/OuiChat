# Chat related endpoints

from ouichat_backend.utils.logger import logger
from ouichat_backend.utils import (
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

from . import _bodies

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
    chat_id = str(uuid.uuid4())

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
    chat_id: str,
    username: str = Depends(decode_sub_access_token)
):
    logger.debug(f"Fetching chat details - username: {username} - conversation_id: {chat_id}")

    # TODO: Add validation method for id's. Could even make a wrapper class over ids with innate validation (use `Depends`)

    chat_doc = await db.get_chat(chat_id)
    if not chat_doc:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, "Chat id not found"
        )
    
    user_in_chat = False
    for participant in chat_doc.preferences.participants:
        if participant.username == username:
            user_in_chat = True
    
    if not user_in_chat:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, "User not a participant of this chat"
        )
    
    logger.info(f"Fetched chat details - username: {username} - conversation_id: {chat_id}")

    return GenericItemResponse(
        item=chat_doc
    )