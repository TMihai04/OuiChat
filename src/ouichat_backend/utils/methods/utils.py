# Utility methods

from ouichat_backend.utils.logger import logger
from ouichat_backend.utils.schemas import (
    ConversationDocument
)

from dotenv import load_dotenv
from datetime import datetime, timezone
from pydantic import BaseModel

import os
import json
import uuid


load_dotenv()


def get_env_str(env_name: str) -> str:
    """Gets the sepcified environment variable as a string. Returns an empty string if env is not set and logs a warning."""
    env_name = env_name.upper()
    env_val = os.getenv(env_name, "")

    if not env_val:
        logger.warning(
            f"(str) `{env_name}` value not set"
        )
    return env_val


def get_env_bool(env_name: str) -> bool:
    """Gets the sepcified environment variable as a boolean. Returns false if env is not set or if it has an invalid value and logs a warning."""
    env_name = env_name.upper()

    valid_true = ["true", "yes", "y", "1"]
    valid_false = ["false", "no", "n", "0"]

    env_val = os.getenv(env_name, "").lower()

    if env_val in valid_true:
        return True
    if env_val in valid_false:
        return False
    
    warning_msg = "is not set" if not env_val else "has an invalid boolean value"
    logger.warning(
        f"(bool) `{env_name}` {warning_msg}"
    )
    return False


def timestamp_now() -> int:
    return int(datetime.now(timezone.utc).timestamp() * 1000)


def datetime_from_timestamp(timestamp: int | float) -> datetime:
    return datetime.fromtimestamp(timestamp, timezone.utc)


def get_participant_flags(
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


def make_sse_event(event: dict | BaseModel) -> str:
    if isinstance(event, dict):
        return "data: {}\n\n".format(json.dumps(event))
    elif isinstance(event, BaseModel):
        return "data: {}\n\n".format(event.model_dump())
    

def get_uuid4() -> str:
    return str(uuid.uuid4())