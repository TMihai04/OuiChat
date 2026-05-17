# Database methods

from ouichat_backend.utils.logger import logger
from ouichat_backend.utils.manager import ws_manager
from ouichat_backend.utils.constants import startup
from ouichat_backend.utils.schemas import (
    UserDocument,
    UserPreferencesDocument,
    WebsocketUpdate,
)
from ouichat_backend.utils.methods import (
    timestamp_now,
)

from pymongo import AsyncMongoClient

import asyncio


async def _ensure_connected(db_uri: str):
    attempts = 0
    max_attempts = 3
    pause = 1.5

    while attempts < max_attempts:
        try:
            await startup.db_client.admin.command("ping")
            return True
        except Exception as e:
            attempts += 1
            sleep_time = pause * 2**attempts

            logger.warning(
                f"Failed to connect client to mongodb. Sleeping {sleep_time}. Retrying attempt {attempts} / {max_attempts}"
            )
            await asyncio.sleep(sleep_time)

            startup.db_client = AsyncMongoClient(host=db_uri, serverSelectionTimeoutMS=2000)
    
    logger.error(
        "Could not connect to mongodb"
    )
    return False


async def connect_client(db_uri: str):
    """Connects singleton client to a mongodb. Attempts connection at most 3 times. Returns `True` if connection was successful and `False` otherwise."""

    startup.db_client = AsyncMongoClient(host=db_uri, serverSelectionTimeoutMS=2000)

    is_connected = await _ensure_connected(db_uri)
    return is_connected


def get_adb(client: AsyncMongoClient, db_name: str):
    """Fetches a db with the given name from the specified client. If any error occurs a log is created and `None` is returned."""
    a_db = None

    try:
        a_db = client[db_name]
    except Exception as e:
        logger.error(f"Failed to fetch database: {e}")
    
    return a_db


def get_acollection(client: AsyncMongoClient, db_name: str, collection_name: str):
    """Fetches a collection with the given name from the specified client and db. If any error occurs a log is created and `None` is returned."""
    a_collection = None

    try:
        a_collection = client[db_name][collection_name]
    except Exception as e:
        logger.error(f"Failed to fetch collection: {e}")
    
    return a_collection


# ================================
# Abstractions for collections
# ================================

def get_users_collection():
    return get_acollection(
        startup.db_client,
        startup.DB_NAME,
        startup.USERS_COLLECTION_NAME
    )


def get_chats_collection():
    return get_acollection(
        startup.db_client,
        startup.DB_NAME,
        startup.CHATS_COLLECTION_NAME
    )


# ================================
# Abstractions for checks
# ================================

async def user_exists(username: str) -> bool:
    collection = get_users_collection()

    one_doc = await collection.find_one(
        filter={
            "username": username,
        }
    )
    if one_doc:
        return True
    return False


# ================================
# Abstractions for operations
# ================================

# User entries
async def add_user(new_user: UserDocument):
    collection = get_users_collection()

    await collection.insert_one(
        new_user.model_dump()
    )

    # Notify websocket of update
    await ws_manager.notify_all(
        payload=WebsocketUpdate(
            type="create",
            scope="user",
            data=new_user.model_dump(include={"username", "profile"})
        ),
        mode="binary"
    )


async def get_user(
    username: str,
    **kwargs,
):
    collection = get_users_collection()
    return await collection.find_one(
        filter={
            "username": username
        },
        **kwargs
    )


async def get_all_users(**kwargs) -> list:
    collection = get_users_collection()
    return await collection.find(
        **kwargs,
    ).to_list(length=None)


async def delete_user(username: str):
    collection = get_users_collection()

    await collection.delete_one(
        filter={
            "username": username
        }
    )

    # Notify websocket of update
    await ws_manager.notify_all(
        payload=WebsocketUpdate(
            type="delete",
            scope="user",
            data={
                "username": username
            }
        ),
        mode="binary"
    )


async def _update_user(
    username: str,
    *,
    update: dict,
    **kwargs
):
    collection = get_users_collection()

    ret = None
    if update:
        ret = await collection.update_one(
            filter={
                "username": username
            },
            update=update,
            **kwargs
        )
    # Update time in different db operation
    ret2 = await collection.update_one(
        filter={
            "username": username
        },
        update={
            "$set": {"updated_at": timestamp_now()}
        }
    )

    return ret or ret2


async def update_user(
    username: str,
    *,
    bl_add: str | None = None,
    bl_del: str | None = None,
    status: str | None = None,
    pic_id: str | None = None,
    login: int | None = None,
):
    upd = None
    if bl_add is not None:
        upd = await _update_user(
            username,
            update={
                "$addToSet": {"preferences.blacklist": bl_add}
            }
        )
        if upd.modified_count == 0:
            return upd
        
        # Notify websocket of update
        await ws_manager.notify_user(
            username=bl_add,
            payload=WebsocketUpdate(
                type="update",
                scope="user.blacklist",
                data={
                    "username": username,
                    "is_blacklisted": True
                }
            ),
            mode="binary"
        )
    
    if bl_del is not None:
        upd = await _update_user(
            username,
            update={
                "$pull": {"preferences.blacklist": {"$eq": bl_del}}
            }
        )
        if upd.modified_count == 0:
            return upd
        
        # Notify websocket of update
        await ws_manager.notify_user(
            username=bl_del,
            payload=WebsocketUpdate(
                type="update",
                scope="user.blacklist",
                data={
                    "username": username,
                    "is_blacklisted": False
                }
            ),
            mode="binary"
        )
    
    if status is not None:
        upd = await _update_user(
            username,
            update={
                "$set": {"profile.status": status}
            }
        )
        if upd.modified_count == 0:
            return upd
        
        # Notify websocket of update
        await ws_manager.notify_all(
            payload=WebsocketUpdate(
                type="update",
                scope="user.status",
                data={
                    "username": username,
                    "status": status
                }
            ),
            mode="binary"
        )
    
    if pic_id is not None:
        upd = await _update_user(
            username,
            update={
                "$set": {"profile.picture_id": pic_id}
            }
        )
        if upd.modified_count == 0:
            return upd
        
        # Notify websocket of update
        await ws_manager.notify_all(
            payload=WebsocketUpdate(
                type="update",
                scope="user.picture",
                data={
                    "username": username,
                    "picture_id": pic_id
                }
            ),
            mode="binary"
        )
    
    if pic_id is not None:
        upd = await _update_user(
            username,
            update={
                "$set": {"last_login": login}
            }
        )
        if upd.modified_count == 0:
            return upd
        
        # Notify websocket of update
        await ws_manager.notify_all(
            payload=WebsocketUpdate(
                type="update",
                scope="user.login",
                data={
                    "username": username,
                    "last_login": login
                }
            ),
            mode="binary"
        )
    
    return upd



