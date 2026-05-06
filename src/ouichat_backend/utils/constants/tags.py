# Tag constants

from enum import Enum


class EndpointTags(Enum):
    AUTHORIZATION: str = "Authorization"
    USERS: str = "Users"


class EndpointPrefixes(Enum):
    USERS: str = "/users"