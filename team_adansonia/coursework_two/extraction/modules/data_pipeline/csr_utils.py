import requests
from io import BytesIO
from PyPDF2 import PdfReader, PdfWriter
import re
import pdfplumber
from pymongo import MongoClient
from team_adansonia.coursework_two.extraction.modules.mongo_db import company_data as mongo
KEYWORDS = ["gallons", "MWh", "pounds", "m3", "water usage", "electricity", "energy", "scope 1", "scope 2", "deforestation", "plastic"]
YEAR_PATTERN = re.compile(r"\b(?:FY\s?\d{2,4}|\b20[1-3][0-9]\b)", re.IGNORECASE)

# Connect to MongoDB
def connect_to_mongo():
    try:
        client = MongoClient("mongodb://localhost:27017/")  # Adjust the connection string if necessary
        return client
    except Exception as e:
        print(f"Error connecting to MongoDB: {e}")
        return None

# Function to get company data from MongoDB based on symbol
def get_company_data_by_symbol(symbol, db):
    company = db.companies.find_one({"symbol": symbol})
    return company

def download_pdf(url: str) -> BytesIO:
    response = requests.get(url)
    response.raise_for_status()
    return BytesIO(response.content)

def filter_pdf_pages(pdf_data: BytesIO) -> tuple[BytesIO, str]:
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


def get_latest_report_url(csr_reports: dict):
    # Ensure csr_reports is a dictionary
    if not isinstance(csr_reports, dict):
        return None

    # Sort the report years in reverse order (most recent first)
    years = sorted(csr_reports.keys(), reverse=True)

    for year in years:
        url = csr_reports.get(year)
        if url:
            return url
    return None


# Main function to run the end-to-end workflow
def run_end_to_end_workflow(company_symbol: str, db):
    # Get company data from MongoDB
    company_data = get_company_data_by_symbol(company_symbol, db)
    if not company_data:
        print(f"No company data found for symbol {company_symbol}")
        return

    # Process CSR report
    print(f"Fetching CSR report for {company_data['security']}")
    filtered_pdf_path = process_csr_report(company_data)

    # Verify that the filtered PDF path is valid and the file is not empty
    if not filtered_pdf_path:
        print(f"Filtered PDF file is either empty or doesn't exist for {company_data['symbol']}")
        return

    print(f"Filtered CSR PDF file saved for {company_data['symbol']}")

    # Perform the rest of the workflow, for example, extracting ESG data
    # This part depends on your specific logic (e.g., extracting ESG data from the CSR report)
    # Assuming you already have a function to process and extract data (not shown here)


# Function to download and filter the CSR report PDF
def process_csr_report(company_data: dict):
    report_url = get_latest_report_url(company_data["csr_reports"])
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
    company_symbol = "MMM"  # Replace with the desired company symbol
    run_end_to_end_workflow(company_symbol, db)
