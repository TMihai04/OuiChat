# Websocket updates schema

from pydantic import BaseModel, Field
from typing import Literal
import uuid


class WebsocketUpdate(BaseModel):
    event_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique identifier for this event",
        min_length=1
    )
    type: Literal["create", "update", "delete", "system"] = Field(
        ...,
        description="The type of update sent through the websocket"
    )
    scope: str = Field(
        ...,
        description="Details about what part of the system registered a change. Formatting details system component",
        pattern=r"^[\w]+(\.[\w]+)*$"
    )
    data: dict = Field(
        ...,
        description="The update data dictionary"
    )