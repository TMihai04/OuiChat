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


class IconBody(BaseModel):
    icon_id: str = Field(
        ...,
        description="Inner id for the selected attachement file",
        min_length=1
    )


class NameBody(BaseModel):
    name: str = Field(
        ...,
        description="Chat display name",
        min_length=1
    )


class DescriptionBody(BaseModel):
    description: str = Field(
        ...,
        description="Chat display description",
        min_length=1
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
    

class AdminStateBody(BaseModel):
    admins: dict[str, bool] = Field(
        ...,
        description="Dictionary of users that will have their admin state altered. Keys are `usernames` and values are wether the user will be an admin or not",
        min_length=1
    )


class ParticipantInviteBody(BaseModel):
    who: list[str] = Field(
        ...,
        description="A list of usernames to be added or reoved from a conversation",
        min_length=1
    )


class SendMessageBody(BaseModel):
    content: str | None = Field(
        None,
        description="Literal text content of the message",
        min_length=1,
        max_length=512
    )
    attachments: list[str] = Field(
        [],
        description="List of attachment ids associated with the message",
        max_length=5
    )
    replied_to: str | None = Field(
        None,
        description="Id of the message this message is a reply to",
        min_length=1
    )

    @model_validator(mode="after")
    def validate_content(self) -> Self:
        if not self.content and not self.attachments:
            raise ValueError("Either `content` or `attachments` must be provided")
        return self


class EditMessageBody(BaseModel):
    message_id: str = Field(
        ...,
        description="Id of the message to be edited",
        min_length=1
    )
    new_content: str = Field(
        ...,
        description="Edited content for the message",
        min_length=1,
        max_length=512
    )


class DeleteMessageBody(BaseModel):
    message_id: str = Field(
        ...,
        description="Id of the message to be deleted",
        min_length=1
    )