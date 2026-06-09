# Tag constants

from enum import Enum


class EndpointTags(Enum):
    AUTHORIZATION: str = "Authorization"
    USERS: str = "Users"
    CHATS: str = "Chats"
    MESSAGES: str = "Messages"
    WEBSOCKET: str = "Websockets"


class EndpointPrefixes(Enum):
    USERS: str = "/users"
    CHATS: str = "/chats"
    MESSAGES: str = "/messages"
    WEBSOCKET: str = "/ws"