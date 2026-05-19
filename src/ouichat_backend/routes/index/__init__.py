from .users import router as users_router
from .chats import router as chat_router
from .websockets import router as ws_router

from fastapi import APIRouter


index_router = APIRouter(
    # prefix="/index"
)

index_router.include_router(users_router)
index_router.include_router(chat_router)
index_router.include_router(ws_router)

__all__ = [
    "index_router",
]