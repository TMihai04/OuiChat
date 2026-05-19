# Endpoint repsonse schemas

from pydantic import (
    BaseModel,
    Field,
    model_validator,
    field_serializer,
)
from typing import Literal


# =================================
# Authentication
# =================================

class NewTokensResponse(BaseModel):
    access_token: str = Field(
        ...,
        description="JWT access token",
    )
    refresh_token: str = Field(
        ...,
        description="JWT refresh token",
    )
    token_type: Literal["bearer"] = Field(
        default="bearer",
        description="Token type",
    )


# =================================
# Misc
# =================================

class GenericMessageResponse(BaseModel):
    message: str = Field(
        default="Success",
        description="Message for a generic response from the API"
    )


class GenericItemsResponse(BaseModel):
    items: list = Field(
        default=[],
        description="List of items for a generic response from the API"
    )


class GenericItemResponse(BaseModel):
    item: dict | BaseModel = Field(
        default={},
        description="Json object for a generic response from the API"
    )

    @field_serializer("item", mode="plain")
    def serialize_item_model(self, item: dict | BaseModel) -> dict:
        if isinstance(item, BaseModel):
            return item.model_dump()
        return item