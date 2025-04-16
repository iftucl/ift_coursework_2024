import json
import requests
import os
from dotenv import load_dotenv
from io import BytesIO
from PyPDF2 import PdfReader, PdfWriter
from extraction.modules.data_pipeline.llama_extractor import LlamaExtractor  # Assuming you have this in a separate script
from extraction.modules.data_pipeline.csr_utils import get_company_data_by_symbol, download_pdf, filter_pdf_pages, get_latest_report_url  # Assuming CSR functions in csr_utils.py
from extraction.modules.validation.validation import validate_and_clean_data
from loguru import logger
import tempfile
import re
from team_adansonia.coursework_two.extraction.modules.mongo_db import company_data as mongo


KEYWORDS = ["gallons", "MWh", "pounds", "m3", "water usage", "electricity", "energy", "scope 1", "scope 2", "deforestation", "plastic"]
YEAR_PATTERN = re.compile(r"\b(?:FY\s?\d{2,4}|\b20[1-3][0-9]\b)", re.IGNORECASE)

# Load environment variables
load_dotenv()
LLAMA_API_KEY = os.getenv("LLAMA_API_KEY")


# Main function to run the end-to-end workflow
def run_end_to_end_workflow(company_symbol: str):
    # Get company data by symbol
    company_data = get_company_data_by_symbol(company_symbol)
    if not company_data:
        logger.error(f"No company data found for symbol {company_symbol}")
        return

    # Process CSR report
    logger.info(f"Fetching CSR report for {company_data['security']}")
    filtered_pdf_path = process_csr_report(company_data)

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

    cleaned_data, issues = validate_and_clean_data(raw_result)

    if issues:
        logger.warning("⚠️ Validation issues found:")
        for issue in issues:
            logger.warning(f" - {issue['category']} > {issue['metric']} ({issue['year']}): {issue['issue']}")
    else:
        logger.success("✅ All metrics validated and normalized successfully.")

    print("\n🎯 Final Cleaned ESG Data (Ready for MinIO or DB):\n")
    print(json.dumps(cleaned_data, indent=2))


# Function to download and filter the CSR report PDF
def process_csr_report(company_data: dict):
    report_url = get_latest_report_url(company_data["csr_reports"])
    if not report_url:
        raise ValueError("No valid CSR report URL found")

    # Download the CSR PDF report
    pdf_data = download_pdf(report_url)

    # Filter the pages of the PDF based on keywords and time series
    filtered_pdf = filter_pdf_pages(pdf_data)

    # Ensure that the filtered PDF is not empty
    if filtered_pdf.getbuffer().nbytes == 0:
        raise ValueError("Filtered PDF is empty, no relevant content found.")

    # Save the filtered PDF to a temporary file
    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
        temp_file.write(filtered_pdf.read())  # Write the filtered PDF content to the temp file
        filtered_pdf_path = temp_file.name  # Get the path of the temporary file

    logger.info(f"Filtered PDF saved to {filtered_pdf_path}")
    return filtered_pdf_path


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
            if not symbol:
                logger.warning("⚠️ Skipping company with no symbol.")
                continue

            try:
                logger.info(f"🚀 Running ESG workflow for: {symbol}")

                # Get latest report URL
                report_url = get_latest_report_url(company.get("csr_reports", []))
                if not report_url:
                    logger.warning(f"⚠️ No valid report found for {symbol}. Skipping.")
                    continue

                # Download & filter CSR report
                pdf_data = download_pdf(report_url)
                filtered_pdf = filter_pdf_pages(pdf_data)

                if filtered_pdf.getbuffer().nbytes == 0:
                    logger.warning(f"⚠️ No relevant content found in CSR report for {symbol}")
                    continue

                # Save temp filtered PDF
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
                    temp_file.write(filtered_pdf.read())
                    filtered_pdf_path = temp_file.name

                # Run extraction
                extractor = LlamaExtractor(
                    api_key=LLAMA_API_KEY,
                    company_name=company["security"],
                    filtered_pdf_path=filtered_pdf_path
                )
                raw_result = extractor.process()
                if not raw_result:
                    logger.warning(f"⚠️ No ESG data extracted for {symbol}")
                    continue

                # Clean and validate
                cleaned_data, issues = validate_and_clean_data(raw_result)


                if issues:
                    logger.warning(f"⚠️ Issues found for {symbol}. Still saving cleaned data.")

                # Append ESG data to the document
                update_result = companies_collection.update_one(
                    {"symbol": company["symbol"]},  # Match by symbol
                    {"$set": {"esg_data": cleaned_data}}  # Set the esg_data field
                )

                logger.success(
                    f"✅ ESG data appended to {symbol} (Matched: {update_result.matched_count}, Modified: {update_result.modified_count})")

            except Exception as e:
                logger.error(f"❌ Failed to process {symbol}: {e}")

    except Exception as db_error:
        logger.error(f"❌ MongoDB operation failed: {db_error}")
    finally:
        mongo_client.close()
        logger.info("🛑 MongoDB connection closed.")
# Entry point
if __name__ == "__main__":
  main()