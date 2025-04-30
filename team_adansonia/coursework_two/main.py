import json
import os
from dotenv import load_dotenv
from team_adansonia.coursework_two.data_pipeline.goals_extractor import call_deepseek_find_goals, extract_goals_by_page
from team_adansonia.coursework_two.data_pipeline.llama_extractor import LlamaExtractor  # Assuming you have this in a separate script
from team_adansonia.coursework_two.data_pipeline.csr_utils import get_company_data_by_symbol, download_pdf, filter_pdf_pages, get_latest_report_url, process_csr_report, get_latest_report_year # Assuming CSR functions in csr_utils.py
from team_adansonia.coursework_two.validation.validation import full_validation_pipeline
from loguru import logger
import tempfile
import re
from team_adansonia.coursework_two.mongo_db import company_data as mongo
from bson import ObjectId
from datetime import datetime

KEYWORDS = ["gallons", "MWh", "pounds", "m3", "water usage", "electricity", "energy", "scope 1", "scope 2", "deforestation", "plastic"]
YEAR_PATTERN = re.compile(r"\b(?:FY\s?\d{2,4}|\b20[1-3][0-9]\b)", re.IGNORECASE)

# Load environment variables
load_dotenv()
LLAMA_API_KEY = os.getenv("LLAMA_API_KEY")


# Main function to run the end-to-end workflow
def run_end_to_end_workflow(company_symbol: str, company_security: str, db, year=None):
    """
    Runs the end-to-end ESG extraction and validation workflow for a given company symbol and security.
    This includes fetching the company's CSR report, extracting ESG data using LlamaExtractor,
    and validating the data using internal checks and OpenAI. It also extracts the company's ESG goals.

    Parameters:
    - company_symbol (str): The stock symbol of the company.
    - company_security (str): The security identifier of the company.
    - db: MongoDB database connection.

    Returns:
    - final_data (dict): Validated and cleaned ESG data.
    - goals (dict): Extracted ESG goals for the company.

    """
    # Get company data by symbol
    company_data = get_company_data_by_symbol(company_symbol, db)
    if not company_data:
        logger.error(f"No company data found for symbol {company_symbol}")
        return

    # Process CSR report
    logger.info(f"Fetching CSR report for {company_data['security']}")
    try:
        filtered_pdf, filtered_text = process_csr_report(company_data, year)
    except Exception as e:
        logger.error(f"No report found: {e}")
        return
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

    goals_text = extract_goals_by_page(filtered_pdf_path)
    goals = call_deepseek_find_goals(company_security, goals_text)
    print(json.dumps(final_data, indent=2))
    return final_data, goals

#Udpate mongo seed
def export_updated_seed_file(db, seed_file="seed_data.json"):
    """
    Exports the updated company data from MongoDB to a seed file. The function retrieves all unique company
    records from the database, processes them (e.g., handles dates and ObjectIds), and writes the data to a JSON file.

    Parameters:
    - db: MongoDB database connection.
    - seed_file (str): The name of the file where the data will be saved (default is "seed_data.json").

    Returns:
    - None: The function directly writes the updated data to a file.

    Example:
    """
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

def run_main_for_symbols(symbols_with_years: list[tuple[str, str | None]]):
    """
    Main driver function that runs the ESG data extraction and update workflow for a list of (symbol, year) pairs.
    The function connects to MongoDB, fetches companies matching the provided symbols, processes CSR reports,
    and updates the company's ESG data and goals in the database.

    Parameters:
    - symbols_with_years (list[tuple[str, str | None]]): A list of (symbol, year) tuples. Year can be None.

    Returns:
    - None
    """
    mongo_client = mongo.connect_to_mongo()
    if mongo_client is None:
        return  # If MongoDB is not connected, terminate the program

    db = mongo_client["csr_reports"]
    companies_collection = db["companies"]

    try:
        # Extract unique symbols to fetch documents from DB
        symbols = [symbol for symbol, _ in symbols_with_years]
        companies = list(companies_collection.find({"symbol": {"$in": symbols}}))

        if not companies:
            logger.warning("⚠️ No matching company documents found in the database.")
            return

        logger.info(f"🔍 Found {len(companies)} matching companies. Starting ESG extraction...\n")

        # Index companies by symbol for faster access
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
                logger.info(f"🚀 Running ESG workflow for: {symbol}, year: {year or 'latest'}")

                field_name_data = f"esg_data_{year}" if year else f"esg_data_{latest_year}"
                field_name_goals = f"esg_goals_{year}" if year else f"esg_goals_{latest_year}"

                # Check if the ESG data for the year already exists
                existing_doc = companies_collection.find_one({"symbol": symbol}, {field_name_data: 1})
                if existing_doc and field_name_data in existing_doc:
                    print(f"ESG data for {symbol} ({year or 'latest'}) already exists. Skipping update.")
                    continue

                # Download & filter CSR report
                cleaned_data, cleaned_goals = run_end_to_end_workflow(symbol, security, db, year)

                # Update ESG data
                companies_collection.update_one(
                    {"symbol": symbol},
                    {"$set": {field_name_data: cleaned_data}}
                )

                # Update ESG goals
                companies_collection.update_one(
                    {"symbol": symbol},
                    {"$set": {field_name_goals: cleaned_goals}}
                )

                logger.success(f"✅ ESG data updated for {symbol} ({year or 'latest'})")

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
    """
       Entry point for running the ESG data extraction and update workflow for all companies in the database.
       The function connects to MongoDB, fetches all companies, processes their CSR reports,
       and updates their ESG data and goals.

       Returns:
       - None: The function performs the workflow and updates MongoDB records for each company.
    """

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
                cleaned_data, cleaned_goals = run_end_to_end_workflow(symbol, security, db)

                update_result_data = companies_collection.update_one(
                    {"symbol": symbol},
                    {"$set": {"esg_data": cleaned_data}}
                )

                update_result_goals = companies_collection.update_one(
                    {"symbol": symbol},
                    {"$set": {"esg_goals": cleaned_goals}}
                )

                logger.success(
                    f"✅ ESG Data fields updated for {symbol} "
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

# Entry point
if __name__ == "__main__":
    symbols_with_years = [
        ("AAPL", "2025"),
        ("sdfsdf", None)
        ]
    run_main_for_symbols(symbols_with_years)