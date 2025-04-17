import os
import re
import sys
import pdfplumber
import asyncio
import nest_asyncio
from typing import List
from pymongo import MongoClient

sys.path.append("C:/Users/86175/Desktop/coursework_two")

from llama_cloud_services import LlamaParse
from llama_index.core import SimpleDirectoryReader, Document
from config.models import model_settings

def find_pages_with_keywords(pdf_path: str, keywords: List[str]) -> List[int]:
    matched_pages = []
    keyword_pattern = re.compile("|".join([re.escape(k) for k in keywords]), re.IGNORECASE)

    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages):
            text = page.extract_text()
            if text and keyword_pattern.search(text):
                matched_pages.append(i)

    print(f"\nPages containing keywords: {matched_pages}")
    return matched_pages

def extract_selected_pages(pdf_path: str, target_pages: List[int]) -> List[Document]:
    parser = LlamaParse(
        api_key=model_settings.LLAMACLOUD_API_KEY,
        result_type="markdown",
        language="en",
        table_extraction_mode="full",
        system_prompt_append="You extract text, metrics, and figures from company sustainability reports.",
        user_prompt="""Extract all text, metrics, and figures from the PDF document.
Return a summary of the extracted text. Return metrics and figures in a table format where possible."""
    )

    reader = SimpleDirectoryReader(
        input_files=[pdf_path],
        file_extractor={".pdf": parser}
    )

    documents = reader.load_data()
    return [doc for i, doc in enumerate(documents) if i in target_pages]

async def main():
    pdf_path = r"C:\Users\86175\Desktop\daima\data\sample-reports\2023-esg-report.pdf"
    keywords = ["CO2 emissions", "carbon", "greenhouse gas", "GHG", "scope 1", "scope 2", "scope 3"]

    target_pages = find_pages_with_keywords(pdf_path, keywords)
    if not target_pages:
        print("No pages containing keywords found.")
        return

    extracted_docs = extract_selected_pages(pdf_path, target_pages)
    print(f"Extracted page count: {len(extracted_docs)}")

    doc_dicts = [
        {
            "text": doc.text,
            "metadata": {
                **doc.metadata,
                "company_name": "company_name",
                "indicator_type": "indicator_type",
                "matched_keywords": keywords
            }
        }
        for doc in extracted_docs
    ]

    os.environ["MONGODB_URI"] = "mongodb+srv://ryan:ThVT4IHQax41RyEG@cluster0.87co0zo.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
    client = MongoClient(os.environ["MONGODB_URI"])
    collection = client["llama_index_db"]["esg_documents"]
    collection.insert_many(doc_dicts)

    print("Documents successfully inserted into MongoDB.")

if __name__ == "__main__":
    nest_asyncio.apply()
    asyncio.get_event_loop().run_until_complete(main())
