# Authentication utilitary methods

from ouichat_backend.utils.logger import logger
from ouichat_backend.utils.constants import startup
from ouichat_backend.utils.constants import (
    password_hash,
    DUMMY_PWD_HASH,
    ALGORITHM,
    ACCESS_TOKEN_EXPIRE_MINS,
    REFRESH_TOKEN_EXPIRE_HRS,
    OAUTH2_SCHEME,
    CREDENTIALS_EXCEPTION,
    WS_CREDENTIALS_EXCEPTION,
)

from .utils import timestamp_now

from datetime import datetime, timedelta, timezone
from fastapi import Depends, Query
from fastapi.security import HTTPAuthorizationCredentials

import re
import jwt


def verify_password(plain_pwd: str, hashed_pwd: str) -> bool:
    return password_hash.verify(plain_pwd, hashed_pwd)


def get_password_hash(plain_pwd: str) -> str:
    return password_hash.hash(plain_pwd)


def get_dummy_hash() -> str:
    return DUMMY_PWD_HASH


def _create_jwt_token(
    data: dict,
    expires_delta: timedelta,
) -> str:
    to_encode = data.copy()

    expire = datetime.now(timezone.utc) + expires_delta
    to_encode["exp"] = expire

    encoded_jwt = jwt.encode(to_encode, startup.SECRET_KEY, ALGORITHM)
    return encoded_jwt


def create_access_token(
    username: str,
) -> str:
    data = {
        "sub": username,
        "iat": datetime.now(timezone.utc),
        "type": "access",
        "roles": ["user"],
    }

    return _create_jwt_token(data, timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINS))


def create_refresh_token(
    username: str,
    token_id: str,
) -> str:
    data = {
        "sub": username,
        "iat": datetime.now(timezone.utc),
        "type": "refresh",
        "jti": token_id,
    }

    return _create_jwt_token(data, timedelta(hours=REFRESH_TOKEN_EXPIRE_HRS))


def decode_token(
    token: str
) -> dict:
    return jwt.decode(token, startup.SECRET_KEY, algorithms=[ALGORITHM])


def decode_sub_access_token(
    credential: HTTPAuthorizationCredentials = Depends(OAUTH2_SCHEME),
) -> str:
    try:
        payload = decode_token(credential.credentials)
    except Exception:
        raise CREDENTIALS_EXCEPTION
    
    if payload.get("type") == "access":
        return payload.get("sub")
    else:
        raise CREDENTIALS_EXCEPTION


def ws_decode_access_token(
    token: str | None = Query(default=None),
) -> dict:
    if not token:
        raise WS_CREDENTIALS_EXCEPTION
    
    try:
        payload = decode_token(token)
    except Exception:
        raise WS_CREDENTIALS_EXCEPTION
    
    if payload.get("type") == "access":
        return payload
    else:
        raise WS_CREDENTIALS_EXCEPTION


def validate_username(username: str) -> tuple[bool, str]:
    if len(username) < 4 or len(username) > 64:
        return False, "Username must be between 4 and 64 characters long (inclusive)"

    reg_exp = r"^[a-zA-Z\-_0-9]{4,64}$"
    if re.search(reg_exp, username) is None:
        return False, "Username contains invalid characters. It can contain lowercase letters (a-z), uppercase letters (A-Z), digits (0-9), hyphens (-), and underscores (_)"
    return True, "ok"


def validate_password(password: str) -> tuple[bool, str]:
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"

    alphabet_dict = {
        "lower": 0,
        "upper": 0,
        "digit": 0,
        "special": 0,
    }
    specials = [".", "_", "-", "!", "/", "+", "=", "*"]

    for char in password:
        if re.match(r"[a-z]", char):
            alphabet_dict["lower"] += 1
        elif re.match(r"[A-Z]", char):
            alphabet_dict["upper"] += 1
        elif re.match(r"[0-9]", char):
            alphabet_dict["digit"] += 1
        elif char in specials:
            alphabet_dict["special"] += 1
        else:
            return False, "Password contains invalid characters. It can contain lowercase letters (a-z), uppercase letters (A-Z), digits (0-9), and special characters (._-!/+=*)"
    
    for key, item in alphabet_dict.items():
        if item == 0:
            return False, "Password must contain at least one of: lowercase letter, uppercase letter, digit, special character"
    return True, "ok"
            

