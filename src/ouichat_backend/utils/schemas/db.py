# Database schemas

from pydantic import (
    BaseModel,
    Field,
    model_validator,
)
from typing import Literal
from typing_extensions import Self


class UserProfileDocument(BaseModel):
    status: str = Field(
        default="Hi there!",
        description="Short text displayed as a status",
        min_length=1,
        max_length=128,
    )
    picture_id: str | None = Field(
        default=None,
        description="Id of an attachement document",
        min_length=1,
    )


class UserPreferencesDocument(BaseModel):
    blacklist: list[str] = Field(
        default=[],
        description="List of usernames this user has 'blocked'"
    )


class UserDocument(BaseModel):
    username: str = Field(
        ...,
        description="Unique identifier of the user. Used both as unique id in the db, and display name",
        min_length=1,
    )
    pwd_hash: str = Field(
        ...,
        description="Hash of the password",
        exclude=True,
        min_length=1,
    )
    profile: UserProfileDocument = Field(
        default=UserProfileDocument(),
        description="User profile information"
    )
    preferences: UserPreferencesDocument = Field(
        default=UserPreferencesDocument(),
        description="User preferences"
    )
    last_login: int | None = Field(
        default=None,
        description="Unix timestamp of last login time"
    )
    created_at: int = Field(
        ...,
        description="Unix timestamp of when this entry was added to the db"
    )
    updated_at: int = Field(
        ...,
        description="Unix timestamp of when this entry was last altered"
    )


class ConversationParticipantDocument(BaseModel):
  username: str = Field(
    ...,
    description="Participant's username"
  )
  is_admin: bool = Field(
    default=False,
    description="Flag that determines wether participant is an admin of the conversation"
  )
  last_seen: int | None = Field(
    default=None,
    description="Timestamp of when the participant last interacted with the conversation"
  )


class ConversationPreferencesDocument(BaseModel):
  participants: list[ConversationParticipantDocument] = Field(
    ...,
    description="List of users taking part in this conversation, plus details"
  )
  created_by: list[str] = Field(
    ...,
    description="Either one (groups) or two (direct) user(s) that created the conversation",
    min_length=1,
    max_length=2
  )

  @model_validator(mode="after")
  def check_at_least_one_admin(self) -> Self:
    for entry in self.participants:
      if entry.is_admin:
        return self
    raise ValueError("At least one admin is required in a conversation")


class ConversationProfileDocument(BaseModel):
  name: str | None = Field(
    default=None,
    description="Display name of the conversation"
  )
  description: str | None = Field(
    default=None,
    description="Display description of the conversation"
  )
  picture_id: str | None = Field(
    default=None,
    description="Display image of the conversation"
  )


class ConversationDocument(BaseModel):
  conversation_id: str = Field(
    ...,
    description="ID of the conversation. UUID4 / UUID7 ? format"
  )
  type: Literal["direct", "group"] = Field(
    ...,
    description="Type of conversation referenced by the document"
  )
  profile: ConversationProfileDocument = Field(
    default=ConversationProfileDocument(),
    description="Display information"
  )
  preferences: ConversationPreferencesDocument = Field(
    ...,
    description="Configuration information"
  )
  created_at: int = Field(
    ...,
    description="Timestamp when this entry was created"
  )
  updated_at: int = Field(
    ...,
    description="Timestamp when this entry was last modified"
  )

  @model_validator(mode="after")
  def validate_profile_by_conv_type(self) -> Self:
    if self.type == "direct":
      if self.profile.name is not None:
        raise ValueError("Direct conversation name cannot be set")
      if self.profile.description is not None:
        raise ValueError("Direct conversation description cannot be set")
      if self.profile.picture_id is not None:
        raise ValueError("Direct conversation picture_id cannot be set")
    elif self.type == "group":
      if self.profile.name is None:
        raise ValueError("Group conversation name must be set")
      if self.profile.description is None:
        raise ValueError("Group conversation description must be set")
    return self