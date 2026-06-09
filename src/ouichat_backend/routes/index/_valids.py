# Validation methods for argument dependencies

from ouichat_backend.utils import (
    ChatId,
    ConversationDocument,
)
from ouichat_backend.utils.methods import (
    db,
    is_valid_uuid,
    get_participant_flags,
    decode_sub_access_token,
)

from fastapi import (
    HTTPException,
    Depends,
    status,
)


def validate_chat_id(chat_id: str) -> ChatId:
    CHAT_ID_EXCEPTION = HTTPException(
        status.HTTP_400_BAD_REQUEST, "Invalid chat id"
    )

    parts = chat_id.split("_")

    if parts[0] not in ["direct", "group"]:
        raise CHAT_ID_EXCEPTION
    if not is_valid_uuid(parts[1]):
        raise CHAT_ID_EXCEPTION
    
    return ChatId(
        type=parts[0],
        id=parts[1]
    )


async def validate_chat(
    chat_id: ChatId = Depends(validate_chat_id)
) -> ConversationDocument:
    chat_doc = await db.get_chat(str(chat_id))
    if not chat_doc:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, "Conversation not found"
        )
    
    return chat_doc


def validate_paricipant(
    username: str = Depends(decode_sub_access_token),
    chat_doc: ConversationDocument = Depends(validate_chat)
) -> dict:
    flags = get_participant_flags(username, chat_doc)

    if not flags.get("participant"):
        raise HTTPException(
            405, "User not a participant of this conversation"
        )
    return flags
    