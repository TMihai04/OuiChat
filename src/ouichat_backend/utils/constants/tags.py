# Tag constants

from enum import Enum


class EndpointTags(Enum):
    AUTHORIZATION: str = "Authorization"
    USERS: str = "Users"
    CHATS: str = "Chats"
    MESSAGES: str = "Messages"
    ATTACHMENTS: str = "Attachments"
    WEBSOCKET: str = "Websockets"


class EndpointPrefixes(Enum):
    USERS: str = "/users"
    CHATS: str = "/chats"
    MESSAGES: str = "/messages"
    ATTACHMENTS: str = "/attachments"
    WEBSOCKET: str = "/ws"