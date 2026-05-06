from .users import router as users_router

from fastapi import APIRouter


index_router = APIRouter(
    # prefix="/index"
)

index_router.include_router(users_router)

__all__ = [
    "index_router",
]