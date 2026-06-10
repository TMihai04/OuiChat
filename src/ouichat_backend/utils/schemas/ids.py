# Identifier schemas

from fastapi.routing import serialize_response
from ouichat_backend.utils.methods import validation

from pydantic import (
    BaseModel,
    Field,
    model_validator,
    model_serializer
)
from typing import Literal
from typing_extensions import Self


class ChatId(BaseModel):
    type: Literal["direct", "group"] = Field(
        ...,
        description="The type of conversation this id references",
    )
    id: str = Field(
        ...,
        description="The actual id of the conversation"
    )

    @model_validator(mode="after")
    def validate_id_type(self) -> Self:
        if validation.is_valid_uuid(self.id):
            return self
        raise ValueError("Malformed conversation id")
    
    @model_serializer(mode="plain")
    def serialize_model(self) -> str:
        return f"{self.type}_{self.id}"
    
    def __str__(self) -> str:
        return self.serialize_model()


class FileId(BaseModel):
    id: str = Field(
        ...,
        description="The actual id of the file"
    )

    @model_validator(mode="after")
    def validate_id_type(self) -> Self:
        if validation.is_valid_uuid(self.id):
            return self
        raise ValueError("Malformed file id")
    
    @model_serializer(mode="plain")
    def serialize_model(self) -> str:
        return self.id
    
    def __str__(self) -> str:
        return self.serialize_model()