import requests
from io import BytesIO
from PyPDF2 import PdfReader, PdfWriter
import re
import pdfplumber
from pymongo import MongoClient
from loguru import logger
import os
from team_adansonia.coursework_two.mongo_db import company_data as mongo
KEYWORDS = ["gallons", "MWh", "pounds", "m3", "water usage", "electricity", "energy", "scope 1", "scope 2", "deforestation", "plastic"]
YEAR_PATTERN = re.compile(r"\b(?:FY\s?\d{2,4}|\b20[1-3][0-9]\b)", re.IGNORECASE)



# Connect to MongoDB
def connect_to_mongo():
    """
    Establishes a connection to the local MongoDB server.

    Returns:
        MongoClient or None: A MongoClient instance if successful, otherwise None.
    """
    try:
        client = MongoClient("mongodb://localhost:27017/")  # Adjust the connection string if necessary
        return client
    except Exception as e:
        print(f"Error connecting to MongoDB: {e}")
        return None

# Function to get company data from MongoDB based on symbol
def get_company_data_by_symbol(symbol, db):
    """
        Retrieves company data from the MongoDB database using the company's stock symbol.

        Args:
            symbol (str): The stock symbol of the company.
            db (Database): The MongoDB database instance.

        Returns:
            dict or None: The company's data if found, otherwise None.
    """
    company = db.companies.find_one({"symbol": symbol})
    return company

def download_pdf(url: str) -> BytesIO | None:
    """
    Downloads a PDF from a given URL.

    Args:
        url (str): The URL of the PDF file.

    Returns:
        BytesIO or None: A stream of the downloaded PDF content, or None if download failed.
    """
    try:
        response = requests.get(url, timeout=10)  # 10-second timeout
        response.raise_for_status()
        return BytesIO(response.content)
    except requests.RequestException as e:
        print(f"❌ Failed to download PDF from {url}: {e}")
        return None

def filter_pdf_pages(pdf_data: BytesIO) -> tuple[BytesIO, str]:
    """
    Filters relevant pages from the PDF that contain ESG-related keywords and time series data.

    Args:
        pdf_data (BytesIO): The original PDF content.

    Returns:
        tuple[BytesIO, str]: A tuple containing:
            - The filtered PDF content as a BytesIO object.
            - Extracted relevant text as a lowercase string.
    """
    reader = PdfReader(pdf_data)
    writer = PdfWriter()
    parsed_text = ""

    with pdfplumber.open(pdf_data) as pdf:
        for i, page in enumerate(pdf.pages):
            text = page.extract_text() or ""
            text_lower = text.lower()

            # Check for keyword presence
            has_keyword = any(kw.lower() in text_lower for kw in KEYWORDS)

            # Check for year mentions (time series)
            years_found = set(YEAR_PATTERN.findall(text))
            has_time_series = len(years_found) >= 2

            if has_keyword and has_time_series:
                writer.add_page(reader.pages[i])
                parsed_text += text + "\n"

    output_pdf = BytesIO()
    writer.write(output_pdf)
    output_pdf.seek(0)

    return output_pdf, parsed_text.strip().lower()

def get_latest_report_year(csr_reports: dict):
    """
    Retrieves the most recent CSR report year key that has a non-empty, non-null URL.

    Args:
        csr_reports (dict): A dictionary mapping years to CSR report URLs.

    Returns:
        int or None: The latest year with a valid report URL, or None if not found.
    """
    if not isinstance(csr_reports, dict):
        return None

    try:
        valid_years = [
            int(year) for year, url in csr_reports.items()
            if (isinstance(year, int) or (isinstance(year, str) and year.isdigit()))
            and url not in (None, "")
        ]
        return max(valid_years) if valid_years else None
    except Exception as e:
        print(f"Error parsing report years: {e}")
        return None


def get_latest_report_url(csr_reports: dict, year=None):
    """
    Retrieves a specific or the most recent CSR report URL from the company's CSR report metadata.

    Args:
        csr_reports (dict): A dictionary mapping years to CSR report URLs.
        year (int, optional): The specific year to retrieve the report for.

    Returns:
        str or None: The URL of the CSR report for the given year, or the most recent one available.
    """
    # Ensure csr_reports is a dictionary
    if not isinstance(csr_reports, dict):
        return None

    # If a specific year is given, try to return its report URL
    if year is not None:
        if csr_reports.get(year):
            return csr_reports.get(year)
        else:
            print(f"No report found for year {year}")
            return None

    # If no specific year is given, return the most recent available report
    for y in sorted(csr_reports.keys(), reverse=True):
        url = csr_reports.get(y)
        if url not in (None, ""):
            return url

    return None


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
        return filtered_pdf, filtered_text
    except Exception as e:
        logger.error(f"No report found: {e}")
        return



# Function to download and filter the CSR report PDF
def process_csr_report(company_data: dict, year=None):
    """
    Downloads and filters the latest CSR report for a company.

    Args:
        company_data (dict): A dictionary containing company information and CSR report URLs.
        year (str, optional): The specific year to retrieve the report for. If None, the most recent report is used.
    Returns:
        tuple[BytesIO, str] or (None, None): The filtered PDF and extracted text, or (None, None) if no relevant content is found.
    """
    report_url = get_latest_report_url(company_data["csr_reports"], year)
    if not report_url:
        print(f"No valid CSR report URL found for {company_data['symbol']}")
        return None

    # Download the CSR PDF report
    pdf_data = download_pdf(report_url)

    # Filter the pages of the PDF based on keywords and time series
    filtered_pdf, filtered_text = filter_pdf_pages(pdf_data)

    # Ensure that the filtered PDF is not empty
    if filtered_pdf.getbuffer().nbytes == 0:
        print(f"Filtered PDF is empty for {company_data['symbol']}, no relevant content found.")
        return None, None

    return filtered_pdf, filtered_text

# Entry point
if __name__ == "__main__":
    # Connect to MongoDB
    mongo_client = mongo.connect_to_mongo()
    if mongo_client is None:
        print("Failed to connect to MongoDB. Exiting.")
        exit()

    # Access the database
    db = mongo_client["csr_reports"]

    # Example: Running workflow for a company symbol "MMM"
    company_symbol = "AMZN"
    company_name = "Amazon "# Replace with the desired company symbol
    run_end_to_end_workflow(company_symbol, company_name, db, "2021")
