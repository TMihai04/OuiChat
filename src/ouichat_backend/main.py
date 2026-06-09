# Main file

from ouichat_backend import _init, config
from ouichat_backend.utils.logger import logger
from ouichat_backend.routes import *

from fastapi import FastAPI
from contextlib import asynccontextmanager


@asynccontextmanager
async def lifespan(app: FastAPI):
    _init.init_logger()

    logger.info("Starting app...")

    _init.init_secret_key()

    await _init.init_mongo_client()

    _init.init_db_name()
    _init.init_db_collections()

    yield


fapi = FastAPI(
    title=config.APP_TITLE,
    description=config.APP_DESCRIPTION,
    lifespan=lifespan,
)


fapi.include_router(auth_router)
fapi.include_router(index_router)