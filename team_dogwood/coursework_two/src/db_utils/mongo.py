"""
MongoDB collection class for interacting with the MongoDB database.
"""

import os
import sys
from datetime import datetime

from typing import List, Union
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
    
    def get_reports_by_company(self, company: Company) -> dict[Union[Union[int, str], Document]]:
        """
        Get a report document by company and its metadata.

        :param company: The company to get the report for.
        :type company: Company
        :return: The report documents.
        :rtype: dict[Union[Union[int, str], Document]]
        """
        try:
            all_reports = {}
            reports = self.collection.find({"company": company.model_dump(exclude={"esg_reports"})})
            for report in reports:
                report_parsed = [Document(**doc) for doc in report["report"]]
                report_metadata = ESGReport(**report["report_metadata"])
                if report:
                    logger.info(f"Report found for {company.security}.")
                    all_reports[report_metadata.year] = report_parsed
            if not all_reports:
                logger.warning(f"No reports found for {company.security}.")
                return None
            return all_reports
        except Exception as e:
            logger.error(f"Error fetching document: {e}")
            return None
        
    def get_available_companies(self) -> List[Company]:
        """
        List all unique companies with parsed reports as Company objects.

        :return: A list of Company objects.
        """
        try:
            pipeline = [
                {"$group": {"_id": "$company", "company": {"$first": "$company"}}},
                {"$replaceRoot": {"newRoot": "$company"}}
            ]
            company_dicts = list(self.collection.aggregate(pipeline))
            return [Company.model_validate(company) for company in company_dicts]
        except Exception as e:
            logger.error(f"Error listing companies from Mongo: {e}")
            return []
        
    def get_available_years(self, mongo_docs: List[dict]) -> List[int]:
        """
        Extract the report year from the report_metadata field in a parsed-report document.

        :param mongo_doc: Document from get_report_by_company().
        :return: List containing the year (e.g. [2023]), or empty list if not found.
        """
        available_years = []
        for mongo_doc in mongo_docs:
            year = mongo_doc.get("report_metadata", {}).get("year")
            if isinstance(year, int):
                available_years.append(year)
            try:
                # If year is a string that can be converted to int
                available_years.append(int(year))
            except (TypeError, ValueError):
                continue
        return list(set(available_years))


if __name__ == "__main__":
    # Example usage
    with MongCollection() as mongo:
        companies = mongo.get_available_companies()
        logger.info(f"{len(companies)} companies found in MongoDB.")
        for company in companies:
            report = mongo.get_report_by_company(company)
            logger.info(f"Report for {company}: {report[0]}")
