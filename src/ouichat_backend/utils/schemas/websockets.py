# Websocket updates schema

from pydantic import BaseModel, Field
from typing import Literal


class WebsocketUpdate(BaseModel):
    type: Literal["create", "update", "delete", "system"] = Field(
        ...,
        description="The type of update sent through the websocket"
    )
    scope: str = Field(
        ...,
        description="Details about what part of the system registered a change. Formatting details system component",
        pattern=r"^[\w]+(.[\w]+)*$"
    )
    data: dict = Field(
        ...,
        description="The update data dictionary"
    )