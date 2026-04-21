import os

from pymongo import MongoClient
from pymongo.errors import ConnectionFailure

MONGO_URL = os.getenv("MONGO_URL")
DB_NAME = os.getenv("MONGO_DB_NAME", "mediDB")

_client: MongoClient | None = None


def get_client() -> MongoClient:
    global _client
    if _client is None:
        _client = MongoClient(MONGO_URL)
    return _client


def get_db():
    return get_client()[DB_NAME]


def ping():
    print(MONGO_URL)
    print(DB_NAME)

    try:
        get_client().admin.command("ping")
        print(f"Connected to MongoDB at {MONGO_URL}")
        return True
    except ConnectionFailure as e:
        print(f"MongoDB connection failed: {e}")
        return False


def close():
    global _client
    if _client is not None:
        _client.close()
        _client = None
