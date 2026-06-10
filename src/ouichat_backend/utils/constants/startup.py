# Variables loaded at application startup

from pymongo import AsyncMongoClient


# =============================================
# Authentication
# =============================================

SECRET_KEY: str | None = None


# =============================================
# Mongo database
# =============================================

db_client: AsyncMongoClient | None = None
DB_NAME: str | None = None
USERS_COLLECTION_NAME: str | None = None
CHATS_COLLECTION_NAME: str | None = None
ATTACHMENTS_COLLECTION_NAME: str | None = None