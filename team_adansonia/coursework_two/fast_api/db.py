from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
from fastapi import HTTPException
import os

_client = None
_db = None

def init_db():
    global _client, _db
    if _db is not None:
        return  # Already initialized

    try:
        if os.path.exists("/.dockerenv"):
            mongo_uri = "mongodb://mongo_db_cw:27017"
        else:
            mongo_uri = "mongodb://localhost:27019"
        print(f"🔌 Connecting to MongoDB at {mongo_uri}")

        _client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
        _client.server_info()  # Check connection
        _db = _client["csr_reports"]
        print("✅ MongoDB connected")
    except ConnectionFailure as e:
        print(f"❌ MongoDB connection failed: {e}")
        raise HTTPException(status_code=500, detail="Database connection failed")
    except Exception as e:
        print(f"❌ Unexpected DB error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

def get_db():
    if _db is None:
        raise RuntimeError("Database not initialized. Call init_db() at startup.")
    return _db

def close_db():
    global _client, _db
    if _client:
        _client.close()
        print("🛑 MongoDB connection closed")
    _client = None
    _db = None
