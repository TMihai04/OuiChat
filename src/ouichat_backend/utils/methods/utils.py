# Utility methods

from ouichat_backend.utils.logger import logger

from dotenv import load_dotenv
from datetime import datetime, timezone

import os


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

    env_val = os.getenv(env_name, "")

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