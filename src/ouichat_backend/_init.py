# App initialization methods

from ouichat_backend.logger import logger
from ouichat_backend.utils.constants import startup
from ouichat_backend.utils.methods import (
    get_env_bool,
    get_env_str,
    db,
)


def init_logger():
    is_debug = get_env_bool("DEBUG")

    if is_debug:
        logger.set_level("DEBUG")
    else:
        logger.set_level("INFO")


def init_secret_key():
    startup.SECRET_KEY = get_env_str("SECRET")
    # NOTE: Remove this log call after finishing authentication !!!!
    logger.debug(
        f"REMOVE THIS WHEN DONE! Secret: {startup.SECRET_KEY}"
    )

    if not startup.SECRET_KEY:
        raise ValueError("Secret key not set")
    logger.info(
        "Successtully obtained secret"
    )


async def init_mongo_client():
    db_uri = get_env_str("MONGODB_URL")
    logger.debug(
        f"Mongo Uri: {db_uri}"
    )
    
    if not await db.connect_client(db_uri):
        raise ValueError("Something went wrong when connecting to mongdb")
    logger.info(
        "Successfully connected to mongdb"
    )


def init_db_name():
    startup.DB_NAME = get_env_str("DB_NAME")
    logger.debug(
        f"DB name: {startup.DB_NAME}"
    )

    if not startup.DB_NAME:
        raise ValueError("Failed to fetch db name")
    logger.info(
        "Successfully fetched db name"
    )


def init_db_collections():
    startup.USERS_COLLECTION_NAME = get_env_str("USERS_COLLECTION_NAME")
    logger.debug(
        f"Users collection name: {startup.USERS_COLLECTION_NAME}"
    )

    if not startup.USERS_COLLECTION_NAME:
        raise ValueError("Failed to fetch users collection name")
    
    startup.CHATS_COLLECTION_NAME = get_env_str("CHATS_COLLECTION_NAME")
    logger.debug(
        f"Chats collectio name: {startup.CHATS_COLLECTION_NAME}"
    )

    if not startup.CHATS_COLLECTION_NAME:
        raise ValueError("Failed to fetch chats collection name")

    logger.info(
        "Successfully fetched collection names"
    )