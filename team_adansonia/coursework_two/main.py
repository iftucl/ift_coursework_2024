import json
import requests
import os
from dotenv import load_dotenv
from io import BytesIO
from PyPDF2 import PdfReader, PdfWriter
from team_adansonia.coursework_two.extraction.modules.data_pipeline.llama_extractor import LlamaExtractor  # Assuming you have this in a separate script
from team_adansonia.coursework_two.extraction.modules.data_pipeline.csr_utils import get_company_data_by_symbol, download_pdf, filter_pdf_pages, get_latest_report_url, process_csr_report # Assuming CSR functions in csr_utils.py
from team_adansonia.coursework_two.extraction.modules.mongo_db.company_data import ROOT_DIR
from team_adansonia.coursework_two.extraction.modules.validation.validation import full_validation_pipeline
from loguru import logger
import tempfile
import re
from team_adansonia.coursework_two.extraction.modules.mongo_db import company_data as mongo
from bson import ObjectId
from datetime import datetime

KEYWORDS = ["gallons", "MWh", "pounds", "m3", "water usage", "electricity", "energy", "scope 1", "scope 2", "deforestation", "plastic"]
YEAR_PATTERN = re.compile(r"\b(?:FY\s?\d{2,4}|\b20[1-3][0-9]\b)", re.IGNORECASE)

# Load environment variables
load_dotenv()
LLAMA_API_KEY = os.getenv("LLAMA_API_KEY")


# Main function to run the end-to-end workflow
def run_end_to_end_workflow(company_symbol: str, company_security: str, db):
    # Get company data by symbol
    company_data = get_company_data_by_symbol(company_symbol, db)
    if not company_data:
        logger.error(f"No company data found for symbol {company_symbol}")
        return

    # Process CSR report
    logger.info(f"Fetching CSR report for {company_data['security']}")
    filtered_pdf, filtered_text = process_csr_report(company_data)

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
        temp_file.write(filtered_pdf.read())
        filtered_pdf_path = temp_file.name

    # Verify that the filtered PDF path is valid and the file is not empty
    if not os.path.exists(filtered_pdf_path) or os.path.getsize(filtered_pdf_path) == 0:
        logger.error(f"Filtered PDF file is either empty or doesn't exist at {filtered_pdf_path}")
        return

    logger.info(f"Filtered CSR PDF file saved at: {filtered_pdf_path}")

    # Use LlamaExtractor to extract ESG metrics
    logger.info(f"Extracting ESG data for {company_data['security']}")
    llama_extractor = LlamaExtractor(
        api_key=LLAMA_API_KEY,
        company_name=company_data["security"],
        filtered_pdf_path=filtered_pdf_path  # Passing the valid file path
    )
    raw_result = llama_extractor.process()

    if not raw_result:
        logger.error("No ESG data extracted from the CSR report.")
        return

    logger.info("✅ Raw extraction complete. Running validation and cleanup...")

    final_data = full_validation_pipeline(raw_result, filtered_text, company_security)

    print(json.dumps(final_data, indent=2))
    return final_data

#Udpate mongo seed
def export_updated_seed_file(db, seed_file="seed_data.json"):
    ROOT_DIR = os.getenv("ROOT_DIR_lOCAL")
    path = os.path.join(ROOT_DIR, "team_adansonia/coursework_two/mongo-seed", seed_file)
    print(
        f"Exporting updated seed file to {seed_file}..."
    )

    collection = db["companies"]
    unique_data = []
    seen_companies = set()

    for doc in collection.find({}):
        company_name = doc.get("security", "")
        if company_name in seen_companies:
            continue
        seen_companies.add(company_name)

        doc.pop("_id", None)
        for key, value in doc.items():
            if isinstance(value, datetime):
                doc[key] = value.isoformat()
            elif isinstance(value, ObjectId):
                doc[key] = str(value)

        unique_data.append(doc)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(unique_data, f, indent=4)

    print(f"✅ Exported {len(unique_data)} unique documents to {seed_file}")
    return


def run_main_for_symbols(symbols: list[str]):
    mongo_client = mongo.connect_to_mongo()
    if mongo_client is None:
        return  # If MongoDB is not connected, terminate the program

    db = mongo_client["csr_reports"]
    companies_collection = db["companies"]

    try:
        # Only fetch companies matching the provided symbols
        companies = list(companies_collection.find({"symbol": {"$in": symbols}}))

        if not companies:
            logger.warning("⚠️ No matching company documents found in the database.")
            return

        logger.info(f"🔍 Found {len(companies)} matching companies. Starting ESG extraction...\n")

        for company in companies:
            symbol = company.get("symbol")
            security = company.get("security")
            if not symbol:
                logger.warning("⚠️ Skipping company, either no symbol or ESG data already exists.")
                continue

            try:
                logger.info(f"🚀 Running ESG workflow for: {symbol}")

                # Download & filter CSR report
                cleaned_data = run_end_to_end_workflow(symbol, security, db)
                # Only update the 'esg_data' field
                update_result = companies_collection.update_one(
                    {"symbol": symbol},
                    {"$set": {"esg_data": cleaned_data}}
                )

                logger.success(
                    f"✅ ESG Data field updated for {symbol} (Matched: {update_result.matched_count}, Modified: {update_result.modified_count})"
                )
                export_updated_seed_file(db)
                logger.success("Updated seed file saved to mongo_seed.json.")

            except Exception as e:
                logger.error(f"❌ Failed to process {symbol}: {e}")


    except Exception as db_error:
        logger.error(f"❌ MongoDB operation failed: {db_error}")
    finally:
        mongo_client.close()
        logger.info("🛑 MongoDB connection closed.")


def main():

    mongo_client = mongo.connect_to_mongo()
    if mongo_client is None:
        return  # If MongoDB is not connected, terminate the program

    # Access the database (not the collection directly)
    db = mongo_client["csr_reports"]
    companies_collection = db["companies"]
    try:
        companies = list(companies_collection.find({}))  # Get full company documents

        if not companies:
            logger.warning("⚠️ No company documents found in the database.")
            return

        logger.info(f"🔍 Found {len(companies)} companies. Starting ESG extraction...\n")

        for company in companies:
            symbol = company.get("symbol")
            security = company.get("security")
            esg_data = company.get("esg_data")
            if not symbol or esg_data is not None:
                logger.warning("⚠️ Skipping company, either no symbol or ESG data already exists.")
                continue

            try:
                logger.info(f"🚀 Running ESG workflow for: {symbol}")
                # Download & filter CSR report
                cleaned_data = run_end_to_end_workflow(symbol, security, db)
                # Append ESG data to the document
                update_result = companies_collection.update_one(
                    {"symbol": company["symbol"]},  # Match by symbol
                    {"$set": {"esg_data": cleaned_data}}  # Set the esg_data field
                )

                logger.success(
                    f"✅ ESG data appended to {symbol} (Matched: {update_result.matched_count}, Modified: {update_result.modified_count})")

                export_updated_seed_file(db)
                logger.success("Updated seed file saved to mongo_seed.json.")

            except Exception as e:
                logger.error(f"❌ Failed to process {symbol}: {e}")

    except Exception as db_error:
        logger.error(f"❌ MongoDB operation failed: {db_error}")
    finally:
        mongo_client.close()
        logger.info("🛑 MongoDB connection closed.")

# Entry point
if __name__ == "__main__":
  run_main_for_symbols(["NVDA"])