"""
Data Lineage Database Writer

This script writes data lineage information to a PostgreSQL database.
It includes error handling for database operations.

The script performs the following operations:
1. Connects to the PostgreSQL database
2. Processes the lineage data
3. Writes the data to the database

Note:
    - Database connection details are configured in the script
    - The data is written to the 'csr_reporting' schema
"""

import base64
import io
import json
import os

import pandas as pd
from cryptography.fernet import Fernet
from sqlalchemy import create_engine

# 硬编码的密钥
ENCRYPTION_KEY = b"FCIWtiOHS3BHySZkTfuEjDuEl8pTUTWiGqxOY8GcfDw="


def find_file(filename, start_path="."):
    """
    Recursively search for a file in the directory structure.

    Args:
        filename (str): Name of the file to search for
        start_path (str, optional): Starting directory for the search. Defaults to ".".

    Returns:
        str: Full path to the found file, or None if not found

    This function:
    1. Recursively walks through the directory structure
    2. Checks each directory for the specified file
    3. Returns the first matching file path found
    """
    for root, dirs, files in os.walk(start_path):
        if filename in files:
            return os.path.join(root, filename)
    return None


def write_data_lineage_to_db():
    """
    Write data lineage information to PostgreSQL database.

    This function:
    1. Establishes a connection to the PostgreSQL database
    2. Processes the lineage data
    3. Writes the processed data to the database
    4. Handles exceptions and provides appropriate error messages

    The function performs the following data processing steps:
    - Processes the lineage data
    - Writes the data to the database

    Raises:
        Exception: For any errors during the process

    Note:
        The function automatically disposes of the database connection
        when finished, regardless of success or failure.
    """
    try:
        # Set PostgreSQL connection information
        db_config = {
            "host": "localhost",
            "port": 5439,
            "database": "fift",
            "user": "postgres",
            "password": "postgres",
        }

        # Create engine using SQLAlchemy
        engine = create_engine(
            f"postgresql+psycopg2://{db_config['user']}:{db_config['password']}@{db_config['host']}:{db_config['port']}/{db_config['database']}"
        )

        # Automatically find lin.json file
        json_path = find_file("lin.json")
        if not json_path:
            raise FileNotFoundError("lin.json file not found")

        # 读取加密的JSON文件
        with open(json_path, "r") as f:
            data = json.load(f)

        # 解码base64字符串
        encrypted_data = base64.b64decode(data["encrypted_data"])

        # 使用Fernet解密
        f = Fernet(ENCRYPTION_KEY)
        decrypted_data = f.decrypt(encrypted_data).decode("utf-8")

        # 将解密后的JSON字符串转换为DataFrame
        df_lineage = pd.read_json(io.StringIO(decrypted_data))

        # Write to PostgreSQL (schema: csr_reporting)
        df_lineage.to_sql(
            "data_lineage",
            engine,
            schema="csr_reporting",
            if_exists="replace",
            index=False,
        )

        print("✅ Data lineage successfully written to PostgreSQL.")
    except Exception as e:
        print("❌ Failed to write data lineage:", e)
    finally:
        engine.dispose()


if __name__ == "__main__":
    write_data_lineage_to_db()
