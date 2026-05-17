# Schemas for post request bodies

from pydantic import BaseModel, Field


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
