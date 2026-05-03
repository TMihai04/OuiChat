# Authorization constants

from pwdlib import PasswordHash
from fastapi.security import OAuth2PasswordBearer, HTTPBearer
from fastapi import HTTPException, status


password_hash = PasswordHash.recommended()
DUMMY_PWD_HASH = password_hash.hash("deadbeefdeadbeef")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINS = 15
REFRESH_TOKEN_EXPIRE_HRS = 2

# OAUTH2_SCHEME = OAuth2PasswordBearer(tokenUrl="login", refreshUrl="refresh")
OAUTH2_SCHEME = HTTPBearer(
    scheme_name="OAuth2 Scheme",
    description="Use this for the 'access token'"
)
REFRESH_SCHEME = HTTPBearer(
    scheme_name="Refresh Scheme",
    description="Use this for the 'refresh token'"
)

CREDENTIALS_EXCEPTION = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Incorrect username or password",
    headers={"WWW-Authenticate": "Bearer"},
)
