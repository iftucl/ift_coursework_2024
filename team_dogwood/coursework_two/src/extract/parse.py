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
from typing import Optional, List
from loguru import logger
import pdfplumber
import re
from src.data_models.documents import ReportKeywords

from llama_cloud_services import LlamaParse
from llama_index.core import SimpleDirectoryReader, Document

from pydantic import BaseModel, Field, PrivateAttr

sys.path.append(os.path.join(os.path.dirname(__file__), "../.."))

from config.models import model_settings
import asyncio


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

    def async_extract_document_pages(self) -> List[Document]:
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
            target_pages=",".join(key_pages),
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
        documents = reader.aload_data()

        self.documents = documents
        return documents


# Process all PDFs in a folder concurrently
async def process_all(mongo_collection, folder: str):
    tasks = []
    for file in os.listdir(folder):
        if file.endswith(".pdf"):
            tasks.append(parse_and_store(mongo_collection, os.path.join(folder, file)))
    await asyncio.gather(*tasks)


# Async function to parse a single file and store result
async def parse_and_store(collection, filepath):
    try:
        docs = await LLamaTextExtractor(filepath).async_extract_document_pages()
        await collection.insert_one({
            "company_name": "",  # from postgres
            "report_year": "",  # from postgres
            "pdf_retrieval_timestamp": "",  # from postgres
            "text_extraction_timesamp": "", # current timestamp
            "filename": os.path.basename(filepath),  # from minio
            "document_pages": [doc.model_dump() for doc in docs]
        })
        logger.info(f"Successfully stored extracted document {filepath}")
    except Exception as e:
        logger.error(f"Unable to process {filepath}: {e}")
    

# Main function to run the script
async def main():
    # 1. initialise postegres db, minio, and mongo client
    # 2. parse all reports from minio to process_all function
    # 3. put extracted text in mongo with metadata
    pass


if __name__ == "__main__":
    # Sample Usage
    pdf_path = f"{os.getcwd()}/data/sample-reports/2023-sustainability-report.pdf"
    logger.info(f"Extracting text from PDF document: {pdf_path}")
    # Extract text
    extractor = LLamaTextExtractor(pdf_path=pdf_path)
    extractor.extract_document_pages()
    logger.info(f"Snippet of Extracted Text: {extractor.documents[5].text}")  # Print the extracted text from a single page
    # write to a markdown file
    logger.info(f"Writing extracted text to markdown file...")
    with open(f"{os.getcwd()}/data/sample-outputs/test.md", "w") as f:
        f.write(extractor.documents[5].text)
        # for doc in extractor.documents:
        #     f.write(doc.text)