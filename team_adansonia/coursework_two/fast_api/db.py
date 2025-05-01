from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
from fastapi import HTTPException
import os

def get_db():
    """
        Establishes a connection to the MongoDB instance and returns the 'csr_reports' database.

        Returns:
            Database: A reference to the 'csr_reports' MongoDB database.

        Raises:
            HTTPException (500): If the database connection fails due to connection issues or unexpected errors.
    """
    try:
        # Ensure the URI is correct based on your environment
        if os.path.exists("/.dockerenv"):
            mongo_uri = "mongodb://mongo_db_cw:27017"
        else:
            mongo_uri = "mongodb://localhost:27019"
        print(f"🔌 Attempting to connect to MongoDB at {mongo_uri}")

        client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
        client.server_info()  # Triggers an exception if MongoDB is unreachable
        print("✅ Successfully connected to MongoDB")

        return client["csr_reports"]  # Return the database instance

    except ConnectionFailure as e:
        print(f"❌ MongoDB connection failed: {e}")
        raise HTTPException(status_code=500, detail="Database connection failed")

    except Exception as e:
        print(f"❌ Unexpected error while connecting to MongoDB: {e}")
        raise HTTPException(status_code=500, detail="Internal server error during DB connection")
