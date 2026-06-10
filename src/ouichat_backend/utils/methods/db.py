# Database methods

from pymongo.asynchronous import collection
from ouichat_backend.utils.logger import logger
from ouichat_backend.utils.manager import ws_manager
from ouichat_backend.utils.constants import startup
from ouichat_backend.utils.schemas import (
    UserDocument,
    ConversationDocument,
    ConversationParticipantDocument,
    MessageDocument,
    AttachmentDocument,
    WebsocketUpdate,
)
from ouichat_backend.utils.methods import (
    timestamp_now,
    get_uuid4
)

from pymongo import AsyncMongoClient, collation

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

    try:
        return client[db_name]
    except Exception as e:
        logger.error(f"Failed to fetch database: {e}")
        raise e


def get_acollection(client: AsyncMongoClient, db_name: str, collection_name: str):
    """Fetches a collection with the given name from the specified client and db. If any error occurs a log is created and `None` is returned."""

    try:
        return client[db_name][collection_name]
    except Exception as e:
        logger.error(f"Failed to fetch collection: {e}")
        raise e


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


def get_message_collection(conv: str):
    return get_acollection(
        startup.db_client,
        startup.DB_NAME,
        conv
    )


def get_attachments_collection():
    return get_acollection(
        startup.db_client,
        startup.DB_NAME,
        startup.ATTACHMENTS_COLLECTION_NAME
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
    event_id = get_uuid4()
    await ws_manager.notify_all(
        payload=WebsocketUpdate(
            event_id=event_id,
            type="create",
            scope="user",
            data=new_user.model_dump(include={"username", "profile"})
        ),
        mode="binary"
    )


async def get_user(
    username: str,
) -> UserDocument | None:
    collection = get_users_collection()

    user_doc = await collection.find_one(
        filter={
            "username": username
        },
    )

    if user_doc is None:
        return None
    
    return UserDocument(**user_doc)


async def get_all_users(
    filter: dict,
    sort: dict = {},
) -> list:
    collection = get_users_collection()
    
    cursor = collection.find(
        filter=filter,
        sort=sort
    )

    ret = []
    async for entry in cursor:
        ret.append(
            UserDocument(**entry)
        )
    return ret


async def delete_user(
    username: str
):
    collection = get_users_collection()

    await collection.delete_one(
        filter={
            "username": username
        }
    )

    # Notify websocket of update
    event_id = get_uuid4()
    await ws_manager.notify_all(
        payload=WebsocketUpdate(
            event_id=event_id,
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
        event_id = get_uuid4()
        await ws_manager.notify_user(
            username=bl_add,
            payload=WebsocketUpdate(
                event_id=event_id,
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
        event_id = get_uuid4()
        await ws_manager.notify_user(
            username=bl_del,
            payload=WebsocketUpdate(
                event_id=event_id,
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
        event_id = get_uuid4()
        await ws_manager.notify_all(
            payload=WebsocketUpdate(
                event_id=event_id,
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
        event_id = get_uuid4()
        await ws_manager.notify_all(
            payload=WebsocketUpdate(
                event_id=event_id,
                type="update",
                scope="user.picture",
                data={
                    "username": username,
                    "picture_id": pic_id
                }
            ),
            mode="binary"
        )
    
    if login is not None:
        upd = await _update_user(
            username,
            update={
                "$set": {"last_login": login}
            }
        )
        if upd.modified_count == 0:
            return upd
        
        # Notify websocket of update
        event_id = get_uuid4()
        await ws_manager.notify_all(
            payload=WebsocketUpdate(
                event_id=event_id,
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


# Conversation entries
async def add_chat(
    new_chat: ConversationDocument
):
    collection = get_chats_collection()

    await collection.insert_one(
        new_chat.model_dump()
    )

    # Notify websocket update
    event_id = get_uuid4()
    for part in new_chat.preferences.participants:
        await ws_manager.notify_user(
            username=part.username,
            payload=WebsocketUpdate(
                event_id=event_id,
                type="create",
                scope="conversation",
                data=new_chat.model_dump()
            ),
            mode="binary"
        )


async def get_chat(
    chat_id: str,
) -> ConversationDocument | None:
    collection = get_chats_collection()
    
    chat_doc = await collection.find_one(
        filter={
            "conversation_id": chat_id
        }
    )

    if chat_doc is None:
        return None
    
    return ConversationDocument(**chat_doc)


async def get_all_chats(
    filter: dict,
    sort: dict = {}
) -> list:
    collection = get_chats_collection()

    cursor = collection.find(
        filter=filter,
        sort=sort
    )

    ret = []
    async for entry in cursor:        
        ret.append(
            ConversationDocument(**entry)
        )
    return ret


async def delete_chat(
    chat_id: str,
    notify: list,
):
    collection = get_chats_collection()

    await collection.delete_one(
        filter={
            "conversation_id": chat_id
        }
    )

    # Delete message collection for this conversation
    msg_collection = get_message_collection(chat_id)

    await msg_collection.drop()

    # Notify websocket of update
    event_id = get_uuid4()
    for user in notify:
        await ws_manager.notify_user(
            username=user,
            payload=WebsocketUpdate(
                event_id=event_id,
                type="delete",
                scope="conversation",
                data={
                    "conversation_id": chat_id
                }
            ),
            mode="binary"
        )


async def _update_chat(
    chat_id: str,
    *,
    update: dict,
    **kwargs
):
    collection = get_chats_collection()

    ret = None
    if update:
        ret = await collection.update_one(
            filter={
                "conversation_id": chat_id
            },
            update=update,
            **kwargs
        )
    # Update time in different db operation
    ret2 = await collection.update_one(
        filter={
            "conversation_id": chat_id
        },
        update={
            "$set": {"updated_at": timestamp_now()}
        }
    )

    return ret or ret2


async def update_chat(
    chat_id: str,
    notify: list,
    *,
    admins: dict | None = None,
    to_add: list | None = None,
    to_remove: list | None = None,
    name: str | None = None,
    description: str | None = None,
    icon_id: str | None = None,
):
    upd = None
    if admins is not None:
        make_admin = []
        remove_admin = []

        for user, state in admins.items():
            if state:
                make_admin.append(user)
            else:
                remove_admin.append(user)

        upd = await _update_chat(
            chat_id,
            update={
                "$set": {
                    "preferences.participants.$[makeAdmin].is_admin": True,
                    "preferences.participants.$[removeAdmin].is_admin": False,
                }
            },
            array_filters=[
                {"makeAdmin.username": {"$in": make_admin}},
                {"removeAdmin.username": {"$in": remove_admin}},
            ]
        )
        if upd.modified_count == 0:
            return upd

        # Notify websocket update
        event_id = get_uuid4()
        for user in notify:
            await ws_manager.notify_user(
                username=user,
                payload=WebsocketUpdate(
                    event_id=event_id,
                    type="update",
                    scope="conversation.admins",
                    data={
                        "conversation_id": chat_id,
                        "make_admin": make_admin,
                        "remove_admin": remove_admin
                    },
                ),
                mode="binary"
            )

    if to_add is not None:
        to_push = []
        for username in to_add:
            to_push.append(
                ConversationParticipantDocument(
                    username=username,
                ).model_dump()
            )
        
        upd = await _update_chat(
            chat_id,
            update={
                "$push": {
                    "preferences.participants": {"$each": to_push}
                }
            }
        )
        if upd.modified_count == 0:
            return upd

        # Notify websocket update
        event_id = get_uuid4()
        for user in notify:
            await ws_manager.notify_user(
                username=user,
                payload=WebsocketUpdate(
                    event_id=event_id,
                    type="update",
                    scope="conversation.participants",
                    data={
                        "conversation_id": chat_id,
                        "operation": "added",
                        "who": to_add
                    },
                ),
                mode="binary"
            )
    
    if to_remove is not None:
        upd = await _update_chat(
            chat_id,
            update={
                "$pull": {
                    "preferences.participants": {
                        "username": {"$in": to_remove}
                    }
                }
            }
        )
        if upd.modified_count == 0:
            return upd

        # Notify websocket update
        event_id = get_uuid4()
        for user in notify:
            await ws_manager.notify_user(
                username=user,
                payload=WebsocketUpdate(
                    event_id=event_id,
                    type="update",
                    scope="conversation.participants",
                    data={
                        "conversation_id": chat_id,
                        "operation": "removed",
                        "who": to_remove
                    },
                ),
                mode="binary"
            )
    
    if name is not None:
        upd = await _update_chat(
            chat_id,
            update={
                "$set": {"profile.name": name}
            }
        )
        if upd.modified_count == 0:
            return upd

        # Notify websocket update
        event_id = get_uuid4()
        for user in notify:
            await ws_manager.notify_user(
                username=user,
                payload=WebsocketUpdate(
                    event_id=event_id,
                    type="update",
                    scope="conversation.name",
                    data={
                        "conversation_id": chat_id,
                        "name": name
                    },
                ),
                mode="binary"
            )        
    
    if description is not None:
        upd = await _update_chat(
            chat_id,
            update={
                "$set": {"profile.description": description}
            }
        )
        if upd.modified_count == 0:
            return upd

        # Notify websocket update
        event_id = get_uuid4()
        for user in notify:
            await ws_manager.notify_user(
                username=user,
                payload=WebsocketUpdate(
                    event_id=event_id,
                    type="update",
                    scope="conversation.description",
                    data={
                        "conversation_id": chat_id,
                        "description": description
                    },
                ),
                mode="binary"
            )
    
    if icon_id is not None:
        upd = await _update_chat(
            chat_id,
            update={
                "$set": {"profile.picture_id": icon_id}
            }
        )
        if upd.modified_count == 0:
            return upd

        # Notify websocket update
        event_id = get_uuid4()
        for user in notify:
            await ws_manager.notify_user(
                username=user,
                payload=WebsocketUpdate(
                    event_id=event_id,
                    type="update",
                    scope="conversation.picture",
                    data={
                        "conversation_id": chat_id,
                        "picture_id": icon_id
                    },
                ),
                mode="binary"
            )
    
    return upd


# Message entries
async def add_message(
    chat: ConversationDocument,
    new_message: MessageDocument
):
    collection = get_message_collection(chat.conversation_id)

    await collection.insert_one(
        new_message.model_dump()
    )

    # Notify websocket update
    event_id = get_uuid4()
    for part in chat.preferences.participants:
        await ws_manager.notify_user(
            username=part.username,
            payload=WebsocketUpdate(
                event_id=event_id,
                type="create",
                scope="message",
                data=new_message.model_dump()
            ),
            mode="binary"
        )


async def get_message(
    chat: ConversationDocument,
    message_id: str
) -> MessageDocument | None:
    collection = get_message_collection(chat.conversation_id)

    message_doc = await collection.find_one(
        filter={
            "message_id": message_id
        }
    )

    if message_doc is None:
        return None
    
    return MessageDocument(**message_doc)


async def get_all_messages(
    chat: ConversationDocument,
    filter: dict,
    sort: dict = {},
    limit: int = 30
):
    collection = get_message_collection(chat.conversation_id)

    cursor = collection.find(
        filter=filter,
        sort=sort
    ).limit(limit)

    ret = []
    async for entry in cursor:
        ret.append(
            MessageDocument(**entry)
        )
    return ret


async def delete_message(
    chat: ConversationDocument,
    message_id: str,
):
    collection = get_message_collection(chat.conversation_id)

    await collection.delete_one(
        filter={
            "message_id": message_id
        }
    )

    # Notify websocket update
    event_id = get_uuid4()
    for part in chat.preferences.participants:
        await ws_manager.notify_user(
            username=part.username,
            payload=WebsocketUpdate(
                event_id=event_id,
                type="delete",
                scope="message",
                data={
                    "message_id": message_id
                }
            ),
            mode="binary"
        )

async def _update_message(
    chat: ConversationDocument,
    message_id: str,
    *,
    update: dict,
    **kwargs
):
    collection = get_message_collection(chat.conversation_id)

    ret = None
    if update:
        ret = await collection.update_one(
            filter={
                "message_id": message_id
            },
            update=update,
            **kwargs
        )
    # Update time in different db operation
    ret2 = await collection.update_one(
        filter={
            "message_id": message_id
        },
        update={
            "$set": {"updated_at": timestamp_now()}
        }
    )

    return ret or ret2


async def update_message(
    chat: ConversationDocument,
    message_id: str,
    *,
    content: str | None = None,
):
    upd = None
    if content is not None:
        upd = await _update_message(
            chat,
            message_id,
            update={
                "$set": {"content": content}
            }
        )
        if upd.modified_count == 0:
            return upd
        
        # Notify websocket update
        event_id = get_uuid4()
        for part in chat.preferences.participants:
            await ws_manager.notify_user(
                username=part.username,
                payload=WebsocketUpdate(
                    event_id=event_id,
                    type="update",
                    scope="message.content",
                    data={
                        "message_id": message_id,
                        "content": content
                    }
                ),
                mode="binary"
            )
    
    return upd


# Attachment entries
async def add_attachment(
    new_file: AttachmentDocument
):
    collection = get_attachments_collection()

    await collection.insert_one(
        new_file.model_dump()
    )


async def get_attachment(
    attachment_id: str
) -> AttachmentDocument | None:
    collection = get_attachments_collection()

    attachment_doc = await collection.find_one(
        filter={
            "attachment_id": attachment_id
        }
    )

    if attachment_doc is None:
        return None
    
    return AttachmentDocument(**attachment_doc)


async def delete_attachment(
    attachment_id: str
):
    collection = get_attachments_collection()

    await collection.delete_one(
        filter={
            "attachment_id": attachment_id
        }
    )