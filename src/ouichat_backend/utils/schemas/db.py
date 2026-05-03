# Database schemas

from pydantic import (
    BaseModel,
    Field,
)


class UserPreferencesDocument(BaseModel):
    blacklist: list[str] = Field(
        default=[],
        description="List of usernames this user has 'blocked'"
    )
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


class UserDocument(BaseModel):
    username: str = Field(
        ...,
        description="Unique identifier of the user. Used both as unique id in the db, and display name",
        min_length=1,
    )
    pwd_hash: str = Field(
        ...,
        description="Hash of the password",
        min_length=1,
    )
    # refresh_jti: str | None = Field(
    #     default=None,
    #     description="Jti of the refresh token that is currently is use for the user",
    #     min_length=1,
    # )
    # refresh_jti_old: list[str] = Field(
    #     default=[],
    #     description="List of jtis from refresh tokens used by this user. Used as protection against token leaks"
    # )
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