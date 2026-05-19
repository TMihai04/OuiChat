# Tag constants

from enum import Enum


class EndpointTags(Enum):
    AUTHORIZATION: str = "Authorization"
    USERS: str = "Users"
    CHATS: str = "Chats"
    WEBSOCKET: str = "Websockets"


class EndpointPrefixes(Enum):
    USERS: str = "/users"
    CHATS: str = "/chats"
    WEBSOCKET: str = "/ws"