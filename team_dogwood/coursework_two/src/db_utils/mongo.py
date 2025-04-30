"""
MongoDB collection class for interacting with the MongoDB database.
"""

import os
import sys
import re
from datetime import datetime

from typing import List
from loguru import logger
from pymongo import MongoClient
from llama_index.core import Document

sys.path.append(os.path.join(os.path.dirname(__file__), "../.."))

from config.db import database_settings
from src.data_models.company import Company, ESGReport


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
    
    def insert_report(self, company: Company, report_metadata: ESGReport, report: List[Document]) -> None:
        """
        Insert a report document into the MongoDB collection.

        :param report_dict: The report document to insert.
        :type report_dict: dict
        """
        try:
            self.collection.insert_one({
                "company": company.model_dump(exclude={"esg_reports"}),
                "report_metadata": report_metadata.model_dump(),
                "text_extraction_timestamp": datetime.now(),
                "report": [doc.model_dump() for doc in report]
            })
            logger.info(f"{company.security}'s report inserted successfully.")
        except Exception as e:
            logger.error(f"Error inserting document: {e}")
    
    def get_report_by_company(self, company: Company) -> List[Document]:
        """
        Get a report document by company.

        :param company: The company to get the report for.
        :type company: Company
        :return: The report documents.
        :rtype: list[Document]
        """
        try:
            report = self.collection.find_one({"company": company.model_dump(exclude={"esg_reports"})})
            report_parsed = [Document(**doc) for doc in report["report"]] if report else []
            if report:
                logger.info(f"Report found for {company.security}.")
                return report_parsed
            else:
                logger.warning(f"No report found for {company.security}.")
                return None
        except Exception as e:
            logger.error(f"Error fetching document: {e}")
            return None
        
    def get_available_companies(self) -> List[str]:
        """
        List all unique company securities with parsed reports.

        :return: A list of strings like ['AAPL', 'MSFT', …].
        """
        try:
            return self.collection.distinct("company.security")
        except Exception as e:
            logger.error(f"Error listing companies from Mongo: {e}")
            return []
        
    def get_available_years(self, mongo_doc: dict) -> List[int]:
        """
        Extract the report year from the report_metadata field in a parsed-report document.

        :param mongo_doc: Document from get_report_by_company().
        :return: List containing the year (e.g. [2023]), or empty list if not found.
        """
        year = mongo_doc.get("report_metadata", {}).get("year")
        if isinstance(year, int):
            return [year]
        try:
            # If year is a string that can be converted to int
            return [int(year)]
        except (TypeError, ValueError):
            return []

