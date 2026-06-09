# Messages related endpoints

from ouichat_backend.utils.logger import logger
from ouichat_backend.utils import (
    ChatId,
    ConversationDocument,
    MessageDocument,
    GenericItemsResponse,
    GenericMessageResponse,
    GenericItemResponse,
    EndpointTags,
    EndpointPrefixes,
)
from ouichat_backend.utils.methods import (
    decode_sub_access_token,
    timestamp_now,
    make_sse_event,
    db,
)

from . import _bodies, _valids

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from typing import Literal

import uuid
import math


router = APIRouter(
    prefix=EndpointPrefixes.MESSAGES.value,
    tags=[EndpointTags.MESSAGES]
)


@router.get(
    "/list",
    status_code=status.HTTP_200_OK
)
async def get_message_batch(
    direction: Literal["old", "mixed", "new"],
    message_id: str | None = None,
    batch_size: int = 30,
    chat: ConversationDocument = Depends(_valids.validate_chat),
    pflags: dict = Depends(_valids.validate_paricipant),
    username: str = Depends(decode_sub_access_token)
) -> StreamingResponse:
    """use this endpoint to get a batch of messages from a target conversation."""

    logger.debug(f"Getting messages - username: {username} - chat_id: {chat.conversation_id} - direction: {direction} - batch_size: {batch_size}")


    def _stream_messages_generator(messages: list):
        for message in messages:
            sse_event = make_sse_event(message)
            yield sse_event.encode("utf-8")


    # Check if message exists
    message_doc = None
    messages = []
    if message_id is not None:
        message_doc = await db.get_message(
            chat,
            message_id
        )
        if not message_doc:
            raise HTTPException(
                status.HTTP_404_NOT_FOUND, "Message not found"
            )
    # Handle newest messages only
    else:
        messages = await db.get_all_messages(
            chat,
            filter={},
            sort={
                "created_at": -1
            },
            limit=batch_size
        )

        messages.reverse()

        logger.info(f"Got newest messages - username: {username} - chat_id: {chat.conversation_id} - batch_size: {batch_size}")

        return StreamingResponse(
            _stream_messages_generator(messages),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no"
            }
        )

    # Handle directional batching
    anchor_timestamp = message_doc.created_at

    # Message order: old -> new
    if direction == "old":
        messages_old = await db.get_all_messages(
            chat,
            filter={
                "$or": [
                    {"created_at": {"$lt": anchor_timestamp}},
                    {"created_at": anchor_timestamp, "message_id": {"$lt": message_id}},
                ]
            },
            sort={
                "created_at": -1,
                "message_id": -1
            },
            limit=batch_size - 1
        )
        
        messages = [message_doc] + messages_old
        messages.reverse()
    elif direction == "new":
        messages_new = await db.get_all_messages(
            chat,
            filter={
                "$or": [
                    {"created_at": {"$gt": anchor_timestamp}},
                    {"created_at": anchor_timestamp, "message_id": {"$gt": message_id}},
                ]
            },
            sort={
                "created_at": 1,
                "message_id": 1
            },
            limit=batch_size - 1
        )
        
        messages = [message_doc] + messages_new
    elif direction == "mixed":
        old_count = math.floor((batch_size - 1) / 2)
        new_count = math.ceil((batch_size - 1) / 2)

        messages_old = await db.get_all_messages(
            chat,
            filter={
                "$or": [
                    {"created_at": {"$lt": anchor_timestamp}},
                    {"created_at": anchor_timestamp, "message_id": {"$lt": message_id}},
                ]
            },
            sort={
                "created_at": -1,
                "message_id": -1
            },
            limit=old_count
        )

        messages_new = await db.get_all_messages(
            chat,
            filter={
                "$or": [
                    {"created_at": {"$gt": anchor_timestamp}},
                    {"created_at": anchor_timestamp, "message_id": {"$gt": message_id}},
                ]
            },
            sort={
                "created_at": 1,
                "message_id": 1
            },
            limit=new_count
        )

        messages_old.reverse()
        messages = messages_old + [message_doc] + messages_new

    logger.info(f"Got messages - username: {username} - chat_id: {chat.conversation_id} - direction: {direction} - batch_size: {batch_size}")

    return StreamingResponse(
        _stream_messages_generator(messages),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no"
        }
    )


@router.post(
    "/send",
    status_code=status.HTTP_201_CREATED
)
async def send_message(
    body: _bodies.SendMessageBody,
    chat: ConversationDocument = Depends(_valids.validate_chat),
    pflags: dict = Depends(_valids.validate_paricipant),
    username: str = Depends(decode_sub_access_token)
) -> GenericMessageResponse:
    """Use this endpoint to send a message to the target conversation."""

    content_preview = f"{body.content[:16]}{"..." if len(body.content) > 16 else ""}" if body.content else None
    logger.debug(f"Sending message - username: {username} - chat_id: {chat.conversation_id} - content: {content_preview} - attachments: {body.attachments}")

    message_id = str(uuid.uuid4())

    new_message = MessageDocument(
        message_id=message_id,
        sender=username,
        content=body.content,
        attachments=body.attachments,
        replied_to=body.replied_to,
        created_at=timestamp_now(),
        updated_at=timestamp_now()
    )

    await db.add_message(
        chat,
        new_message,
    )

    logger.info(f"Sent message - username: {username} - chat_id: {chat.conversation_id}")

    return GenericMessageResponse(
        message="Success"
    )


@router.post(
    "/edit",
    status_code=status.HTTP_200_OK
)
async def edit_message(
    body: _bodies.EditMessageBody,
    chat: ConversationDocument = Depends(_valids.validate_chat),
    pflags: dict = Depends(_valids.validate_paricipant),
    username: str = Depends(decode_sub_access_token)
) -> GenericMessageResponse:
    """Use this endpoint to edit the text content of a sent message"""

    content_preview = f"{body.new_content[:16]}{"..." if len(body.new_content) > 16 else ""}"
    logger.debug(f"Editing message - username: {username} - chat_id: {chat.conversation_id} - new_content: {content_preview}")

    # Check if message exists and if current user is sender
    message_doc = await db.get_message(chat, body.message_id)
    if not message_doc:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, "Message id not found"
        )
    if username != message_doc.sender:
        raise HTTPException(
            405, "Can only edit self sent message"
        )
    
    # Update message
    message = "Success"
    update = await db.update_message(
        chat,
        message_doc.message_id,
        content=body.new_content
    )
    if update.modified_count == 0:
        message = "Unchanged"

    logger.info(f"Edited message - username: {username} - chat_id: {chat.conversation_id}")

    return GenericMessageResponse(
        message=message
    )


@router.delete(
    "/delete",
    status_code=status.HTTP_204_NO_CONTENT
)
async def delete_message(
    body: _bodies.DeleteMessageBody,
    chat: ConversationDocument = Depends(_valids.validate_chat),
    pflags: dict = Depends(_valids.validate_paricipant),
    username: str = Depends(decode_sub_access_token)
):
    """Use this endpoint to delete a message from a target conversation."""

    logger.debug(f"Deleting message - username: {username} - chat_id: {chat.conversation_id} - message_id: {body.message_id}")

    # Check deletion permissions based on admin rights
    if not pflags.get("admin"):
        message_doc = await db.get_message(chat, body.message_id)
        if not message_doc:
            raise HTTPException(
                status.HTTP_404_NOT_FOUND, "Message not found"
            )
        if username != message_doc.sender:
            raise HTTPException(
                405, "Only admins can delete not sent messages"
            )

    await db.delete_message(
        chat,
        body.message_id
    )

    logger.info(f"Deleted message - username: {username} - chat_id: {chat.conversation_id} - message_id: {body.message_id}")