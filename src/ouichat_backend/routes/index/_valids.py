# Validation methods for argument dependencies

from ouichat_backend.utils import (
    ChatId,
)
from ouichat_backend.utils.methods import (
    is_valid_uuid,
)

from fastapi import (
    HTTPException,
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
    