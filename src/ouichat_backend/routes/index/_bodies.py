# Schemas for post request bodies

from pydantic import BaseModel, Field, model_validator
from typing import Literal
from typing_extensions import Self


class BlacklistBody(BaseModel):
    who: str = Field(
        ...,
        description="Target username to be added in the calling user's blacklist",
        min_length=1
    )


class StatusBody(BaseModel):
    status: str = Field(
        ...,
        description="Display status for user",
        min_length=1,
        max_length=128
    )


class _GroupData(BaseModel):
    name: str = Field(
        ...,
        description="Name of the group",
        min_length=1
    )
    description: str = Field(
        ...,
        description="Description for the group",
        min_length=1
    )
    picture_id: str | None = Field(
        None,
        description="Display picture for the group",
        min_length=1
    )


class NewChatBody(BaseModel):
    type: Literal["direct", "group"] = Field(
        ...,
        description="Type of conversation"
    )
    group: _GroupData | None = Field(
        None,
        description="Group information such as name, description, and picture. Entry can be ommited if a direct conversation is being created"
    )
    participants: dict[str, bool] = Field(
        ...,
        description="Dictionary of participants to the chat. Format: `key`: username, `value`: wether the user is an admin of the conversation"
    )

    @model_validator(mode="after")
    def validate_group_data(self) -> Self:
        if self.type == "group" and self.group is None:
            raise ValueError("Group data must be provided for `group` type conversation")
        return self
    
    @model_validator(mode="after")
    def validate_participant_count(self) -> Self:
        if self.type == "direct" and len(self.participants) != 2:
            raise ValueError("`direct` type conversation can only contain 2 members")
        elif self.type == "group" and len(self.participants) < 1:
            raise ValueError("`group` type conversation must have at least one member")
        return self
    
    @model_validator(mode="after")
    def validate_admins(self) -> Self:
        if self.type == "group" and True not in self.participants.values():
            raise ValueError("`group` type conversations must have at least one admin")
        return self