"""
End-to-End ESG Data Extraction and MongoDB Integration Script

This module orchestrates the full data pipeline for extracting Environmental, Social,
and Governance (ESG) data from CSR reports using AI-powered tools (LLaMA and DeepSeek),
processing it, validating it, storing it in MongoDB, and exporting the result to a seed JSON file.

Main Functions:
- run_end_to_end_workflow: Processes a company's CSR report and extracts ESG data and goals.
- run_main_for_symbols: Batch processes a list of company symbols and updates the database.
- export_updated_seed_file: Dumps the MongoDB 'companies' collection to a JSON seed file.
- main: Main loop for processing all companies in the database (used for bulk updates).
"""

import os
import re
import json
import tempfile
import asyncio
from loguru import logger
from bson import ObjectId
from datetime import datetime
from dotenv import load_dotenv
from mongo_db import company_data as mongo
from validation.validation import full_validation_pipeline
from data_pipeline.goals_extractor import call_deepseek_find_goals, extract_goals_by_page
from data_pipeline.llama_extractor import LlamaExtractor
from data_pipeline.csr_utils import (
    get_company_data_by_symbol,
    download_pdf,
    filter_pdf_pages,
    get_latest_report_url,
    process_csr_report,
    get_latest_report_year,
)

KEYWORDS = ["gallons", "MWh", "pounds", "m3", "water usage", "electricity", "energy", "scope 1", "scope 2", "deforestation", "plastic"]
YEAR_PATTERN = re.compile(r"\b(?:FY\s?\d{2,4}|\b20[1-3][0-9]\b)", re.IGNORECASE)

# Load environment variables
load_dotenv(override=True)
LLAMA_API_KEY = os.getenv("LLAMA_API_KEY")


async def run_end_to_end_workflow(company_symbol: str, company_security: str, db, year=None):
    """
    Executes the full ESG extraction workflow for a single company.

    Steps:
    1. Fetch CSR report (filtered).
    2. Run LLaMA extractor on PDF.
    3. Run ESG data validation pipeline.
    4. Extract goals using DeepSeek.

    Parameters:
    - company_symbol (str): The stock ticker symbol of the company.
    - company_security (str): The full name of the company.
    - db: MongoDB database connection.
    - year (int or None): Optional CSR report year to target.

    Returns:
    - tuple: (validated_esg_data: dict, esg_goals: dict)
    """
    company_data = get_company_data_by_symbol(company_symbol, db)
    if not company_data:
        logger.error(f"No company data found for symbol {company_symbol}")
        return {}, {}

    logger.info(f"Fetching CSR report for {company_data['security']}")
    try:
        filtered_pdf, filtered_text = process_csr_report(company_data, year)
        #print first few lines
        print(filtered_text[:10])
    except Exception as e:
        logger.error(f"No report found: {e}")
        return {}, {}

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
        temp_file.write(filtered_pdf.read())
        filtered_pdf_path = temp_file.name

    if not os.path.exists(filtered_pdf_path) or os.path.getsize(filtered_pdf_path) == 0:
        logger.error(f"Filtered PDF file is either empty or doesn't exist at {filtered_pdf_path}")
        return {}, {}

    logger.info(f"Filtered CSR PDF file saved at: {filtered_pdf_path}")

    #try read from filtered_pdf_path
    with open(filtered_pdf_path, "rb") as pdf_file:
        print(pdf_file.read(10))
        print("read ok")

    llama_extractor = LlamaExtractor(
        api_key=LLAMA_API_KEY,
        company_name=company_data["security"],
        filtered_pdf_path=filtered_pdf_path
    )

    raw_result = await llama_extractor.process()

    print('raw result', raw_result)

    if not raw_result:
        logger.error("No ESG data extracted from the CSR report.")
        return {}, {}

    logger.info("✅ Raw extraction complete. Running validation and cleanup...")

    final_data = full_validation_pipeline(raw_result, filtered_text, company_security, filtered_pdf_path)

    goals_text = extract_goals_by_page(filtered_pdf_path)
    goals = call_deepseek_find_goals(company_security, goals_text)

    return final_data, goals


def export_updated_seed_file(db, seed_file="seed_data.json"):
    """
    Exports current MongoDB company data into a JSON seed file.

    Handles ISO conversion for dates and string conversion for ObjectIds.

    Parameters:
    - db: MongoDB database connection.
    - seed_file (str): Filename for the seed output (default: "seed_data.json").

    Returns:
    - None
    """
    ROOT_DIR = os.getenv("ROOT_DIR_LOCAL")
    path = os.path.join(ROOT_DIR, "mongo-seed", seed_file)
    print(f"Exporting updated seed file to {seed_file}...")

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


async def run_main_for_symbols(symbols_with_years: list[tuple[str, str | None]]):
    """
    Executes the ESG extraction pipeline for a given list of company symbols and target years.

    Parameters:
    - symbols_with_years (list[tuple[str, str | None]]): List of (symbol, year) pairs.

    Returns:
    - None
    """
    mongo_client = mongo.connect_to_mongo()
    if mongo_client is None:
        return

    db = mongo_client["csr_reports"]
    companies_collection = db["companies"]

    try:
        symbols = [symbol for symbol, _ in symbols_with_years]
        companies = list(companies_collection.find({"symbol": {"$in": symbols}}))
        if not companies:
            logger.warning("⚠️ No matching company documents found.")
            return

        logger.info(f"🔍 Found {len(companies)} matching companies...")

        company_dict = {company["symbol"]: company for company in companies}

        for symbol, year in symbols_with_years:
            company = company_dict.get(symbol)
            if not company:
                logger.warning(f"⚠️ No company data found for symbol {symbol}. Skipping.")
                continue

            latest_year = get_latest_report_year(company.get("csr_reports", {}))
            security = company.get("security")
            if not symbol:
                logger.warning("⚠️ Skipping company, no symbol present.")
                continue

            try:
                field_name_data = f"esg_data_{year}" if year else f"esg_data_{latest_year}"
                field_name_goals = f"esg_goals_{year}" if year else f"esg_goals_{latest_year}"

                existing_doc = companies_collection.find_one({"symbol": symbol}, {field_name_data: 1})
                if existing_doc and field_name_data in existing_doc:
                    logger.info(f"ESG data for {symbol} ({year or latest_year}) already exists. Skipping.")
                    continue

                # Set the status to processing
                companies_collection.update_one(
                    {"symbol": symbol},
                    {"$set": {field_name_data: "processing"}}
                )
                companies_collection.update_one(
                    {"symbol": symbol},
                    {"$set": {field_name_goals: "processing"}}
                )

                logger.info(f"🚀 Running ESG workflow for: {symbol}, year: {year or latest_year}")

                cleaned_data, cleaned_goals = await run_end_to_end_workflow(symbol, security, db, year)
                if cleaned_data:
                    companies_collection.update_one(
                        {"symbol": symbol},
                        {"$set": {field_name_data: cleaned_data}}
                    )
                if cleaned_goals:
                    companies_collection.update_one(
                        {"symbol": symbol},
                        {"$set": {field_name_goals: cleaned_goals}}
                    )

                logger.success(f"✅ ESG data updated for {symbol} ({year or latest_year})")

                export_updated_seed_file(db)
                logger.success("Updated seed file saved to mongo_seed.json.")

            except Exception as e:
                #remove status from the company
                companies_collection.update_one(
                    {"symbol": symbol},
                    {"$unset": {field_name_data: "", field_name_goals: ""}}
                )
                logger.error(f"❌ Failed to process {symbol}: {e}")

    finally:
        mongo_client.close()
        logger.info("🛑 MongoDB connection closed.")


def get_unextracted_symbol_years_mongo(n=10):
    """
    Retrieves a list of company symbols and years for which ESG data has not been extracted.

    This function searches through the companies collection in the MongoDB database and checks
    each company's CSR report links to find years that have not yet been processed for ESG data.
    It returns a list of up to n such (symbol, year) pairs.
    """
    mongo_client = mongo.connect_to_mongo()
    if mongo_client is None:
        return

    db = mongo_client["csr_reports"]
    companies_collection = db["companies"]
    
    unextracted = []
    cursor = companies_collection.find({}, {"symbol": 1, "csr_reports": 1, "_id": 0})

    for doc in cursor:
        symbol = doc.get("symbol")
        csr_reports = doc.get("csr_reports", {})

        for year in sorted(csr_reports):
            url = csr_reports[year]
            if url and f"esg_data_{year}" not in doc:
                unextracted.append((symbol, year))
                if len(unextracted) == n:
                    return unextracted

    return sorted(unextracted, key=lambda x: int(x[1]))

def main():
    """
    Runs the full ESG data extraction workflow for every company in the MongoDB database.

    Only processes companies that are missing ESG data for the latest CSR report year.
    """
    mongo_client = mongo.connect_to_mongo()
    if mongo_client is None:
        return

    db = mongo_client["csr_reports"]
    companies_collection = db["companies"]

    try:
        companies = list(companies_collection.find({}))
        if not companies:
            logger.warning("⚠️ No company documents found in the database.")
            return

        logger.info(f"🔍 Found {len(companies)} companies. Starting ESG extraction...\n")

        for company in companies:
            symbol = company.get("symbol")
            security = company.get("security")

            if not symbol:
                logger.warning("⚠️ Skipping company, no symbol present.")
                continue

            latest_year = get_latest_report_year(company.get("csr_reports", {}))
            if not latest_year:
                logger.warning(f"⚠️ No valid CSR report year for {symbol}. Skipping.")
                continue

            field_name_data = f"esg_data_{latest_year}"
            field_name_goals = f"esg_goals_{latest_year}"

            existing_doc = companies_collection.find_one({"symbol": symbol}, {field_name_data: 1})
            if existing_doc and field_name_data in existing_doc:
                logger.info(f"ESG data for {symbol} ({latest_year}) already exists. Skipping.")
                continue

            try:
                logger.info(f"🚀 Running ESG workflow for: {symbol}, year: {latest_year}")
                cleaned_data, cleaned_goals = asyncio.run(run_end_to_end_workflow(symbol, security, db, None))

                if cleaned_data:
                    companies_collection.update_one(
                        {"symbol": symbol},
                        {"$set": {field_name_data: cleaned_data}}
                    )
                if cleaned_goals:
                    companies_collection.update_one(
                        {"symbol": symbol},
                        {"$set": {field_name_goals: cleaned_goals}}
                    )

                logger.success(f"✅ ESG data updated for {symbol} ({latest_year})")
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
    symbols_with_years = [("NVDA", "2021")]
    mongo.import_seed_to_mongo()
    asyncio.run(run_main_for_symbols(symbols_with_years))
