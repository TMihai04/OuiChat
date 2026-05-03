# Endpoint repsonse schemas

from pydantic import (
    BaseModel,
    Field,
    model_validator,
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

class GenericResponse(BaseModel):
    message: str = Field(
        default="Success",
        description="Message for a generic response from the API"
    )