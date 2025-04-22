"""
MongoDB collection class for interacting with the MongoDB database.
"""

import os
import sys
from datetime import datetime

from typing import List
from loguru import logger
from pymongo import MongoClient
from llama_index.core import Document

sys.path.append(os.path.join(os.path.dirname(__file__), "../.."))

from config.db import database_settings
from src.data_models.company import Company


class MongCollection:
    """
    MongoDB collection class for interacting with the MongoDB database.
    """

    def __init__(self):
        self.client = MongoClient(database_settings.MONGO_URI)
        self.db = self.client[database_settings.MONGO_DB_NAME]
        self.collection = self.db[database_settings.MONGO_COLLECTION_NAME]

    def __enter__(self):
        """
        Enter the runtime context related to this object.

        :return: The instance of the MongoCollection class.
        :rtype: MongoCollection
        """
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """
        Exit the runtime context.

        :param exc_type: The exception type (if any).
        :param exc_val: The exception value (if any).
        :param exc_tb: The traceback (if any).
        """
        if self.client:
            self.client.close()
        if exc_type:
            print(f"Exception occurred: {exc_type}, {exc_value}")
            # Return False to propagate the exception
            return False
    
    async def insert_report(self, company: Company, report: List[Document]) -> None:
        """
        Insert a report document into the MongoDB collection.

        :param report_dict: The report document to insert.
        :type report_dict: dict
        """
        try:
            self.collection.insert_one({
                "company": company.model_dump(),
                "text_extraction_timestamp": datetime.now(),
                "report": [doc.model_dump() for doc in report]
            })
            logger.info(f"{company.security}'s report inserted successfully.")
        except Exception as e:
            logger.error(f"Error inserting document: {e}")
