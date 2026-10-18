# Main file

from ouichat_backend import _init, config
from ouichat_backend.utils.logger import logger
from ouichat_backend.routes import *

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager


@asynccontextmanager
async def lifespan(app: FastAPI):
    _init.init_logger()

    logger.info("Starting app...")

    _init.init_secret_key()

    await _init.init_mongo_client()

    _init.init_db_name()
    _init.init_db_collections()

    _init.init_file_dirs()

    yield


fapi = FastAPI(
    title=config.APP_TITLE,
    description=config.APP_DESCRIPTION,
    lifespan=lifespan,
)

# The web client is served from a different origin than the domain typed at
# login. These headers let that page read HTTP responses. Tokens are sent in
# the Authorization header, not cookies, so a wildcard origin is safe here.
fapi.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],
)

fapi.include_router(auth_router, prefix="/api")
fapi.include_router(index_router, prefix="/api")
fapi.include_router(ws_router)