from .token import router as token_router
from .accounts import router as accounts_router

from fastapi import APIRouter


auth_router = APIRouter()

auth_router.include_router(token_router)
auth_router.include_router(accounts_router)


__all__ = [
    "auth_router",
]

