"""
Methods for text extraction from PDF documents.

Main script extracts text from a PDF document using LlamaParse and saves the extracted document to MongoDB.

# Remaining Tasks - Devs
# Implementation of vector store for querying (targeted searches of specific figures)
    # 1. Read extracted text from mongo and create a vector store
    # 2. Query store to get specific figures
# Orchestration of parsing, extraction, and storage. Final script should:
    # 1. Reads company details from the sql database, 
    # 2. Look for a company report on minio,
    # 3. (Iman) Extract text and store the full report text in mongo
    # 4. (Sardor) Use the extracted text from mongo to extract metrics (in a structured format) and store in SQL (could use data sink feature of Llama to do this)
# Scheduling of script for refreshing metrics - Iman
# Basic UI for visualisation - Sardon done
# Code for visualising metric information (for a single company and comparison with multiple companies) - Siyu
# Figure out how to pass around and persist metadata - Iman

# Remaining Tasks - Owners / Specialists
# 1. Switch to sphinx-style docstrings (Gabriella)
# 2. Finalise data catalogue, dictionary, data validation rules, etc. (To be updated once devs have finished)
# 3. Create architecture diagrams 
# 4. Write final report
"""
import os
import sys
import asyncio
import tempfile
from typing import Optional, List
from loguru import logger
import pdfplumber
import re
import logging
logging.getLogger("PyPDF2").setLevel(logging.WARNING)

from llama_cloud_services import LlamaParse
from llama_index.core import SimpleDirectoryReader, Document

from pydantic import BaseModel, Field, PrivateAttr

sys.path.append(os.path.join(os.path.dirname(__file__), "../.."))

from src.data_models.documents import ReportKeywords
from config.models import model_settings
from src.db_utils.mongo import MongCollection
from src.db_utils.postgres import PostgreSQLDB
from src.db_utils.minio import MinioFileSystem
from src.db_utils.helpers import get_all_companies, append_reports_to_companies


class LLamaTextExtractor(BaseModel):
    """
    Class for extracting text from PDF documents using LlamaParse.
    """

    # pdf document path
    pdf_path: str = Field(
        ...,
        description="Path to the PDF document to extract text from.",
    )

    # parsed documents
    documents: Optional[List[Document]] = Field(
        None,
        description="List of extracted documents.",
    )

    # LlamaParse API key
    _llama_api_key: str = PrivateAttr(model_settings.LLAMACLOUD_API_KEY)

    @staticmethod
    def find_pages_with_keywords(pdf_path: str) -> List[int]:
        matched_pages = []
        keywords = [k.value for k in ReportKeywords]
        keyword_pattern = re.compile("|".join([re.escape(k) for k in keywords]), re.IGNORECASE)

        with pdfplumber.open(pdf_path) as pdf:
            for i, page in enumerate(pdf.pages):
                text = page.extract_text()
                if text and keyword_pattern.search(text):
                    matched_pages.append(i)

        logger.debug(f"\nPages containing keywords: {matched_pages}")
        return matched_pages

    async def async_extract_document_pages(self) -> List[Document]:
        """
        Extract text from the PDF document using LlamaParse.

        Returns:
            list[Document]: per page extracted text from the PDF document.
                text can be accessed via documents[0].text
        """
        key_pages = self.find_pages_with_keywords(self.pdf_path)
        # Initialize LlamaParse with the API key
        parser = LlamaParse(
            api_key=self._llama_api_key,
            result_type="markdown",
            target_pages=",".join(map(str, key_pages)),
            language="en",
            table_extraction_mode="full",
            system_prompt_append="You extract text, metrics, and figures from company sustainability reports.",
            user_prompt="""\
Extract all text, metrics, and figures from the PDF document.
Return a summary of the extracted text. Return metrics and figures in a table format where possible.
\
""")

        # Use SimpleDirectoryReader to read the PDF document
        file_extractor = {".pdf": parser}
        reader = SimpleDirectoryReader(input_files=[self.pdf_path], file_extractor=file_extractor)
        documents = await reader.aload_data()

        logger.info(f"Extracted {len(documents)} pages from {self.pdf_path}")

        self.documents = documents
        return documents


# Main function to run the script
async def main():
    # 1. initialise postegres db, minio, and mongo client
    postgres = PostgreSQLDB()
    minio = MinioFileSystem()
    mongo = MongCollection()

    # 2. get all company and report data from postgres
    companies = get_all_companies(postgres)
    companies = append_reports_to_companies(companies, postgres)

    # 3. For each company, process each report from minio
    async def process_report(company, report):
        company_name = company.security
        report_path = f"{company.security}/{report.year}/{os.path.basename(report.url)}"
        if not report_path:
            return
        logger.info(f"Processing report {report_path} for company {company_name}")

        # Check if report exists in Minio (sync -> async)
        available_files = await asyncio.to_thread(minio.list_files_by_company, company.security)
        if report_path not in available_files:
            logger.warning(f"Report {report_path} does not exist in Minio. Skipping.")
            return

        # Fetch PDF as bytes from Minio (sync -> async)
        pdf_bytes = await asyncio.to_thread(minio.get_pdf_bytes, report_path)
        if not pdf_bytes:
            logger.warning(f"Failed to fetch PDF bytes for {report_path} in Minio for company '{company.security}'. Skipping.")
            return

        # Write bytes to a NamedTemporaryFile
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=True) as tmp_pdf:
            tmp_pdf.write(pdf_bytes)
            tmp_pdf.flush()

            # Extract text using LLamaTextExtractor
            try:
                extractor = LLamaTextExtractor(pdf_path=tmp_pdf.name)
                docs = await extractor.async_extract_document_pages()
            except Exception as e:
                logger.error(f"Extraction failed for {report_path}: {e}")
                return

            # Store in MongoDB (sync -> async)
            try:
                await asyncio.to_thread(mongo.insert_report, company, docs)
            except Exception as e:
                logger.error(f"Failed to store extracted document for {report_path}: {e}")

    # Create tasks for all company/report pairs
    tasks = []
    for company in companies:
        for report in company.esg_reports:
            tasks.append(process_report(company, report))
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(main())