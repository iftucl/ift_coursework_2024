import os
import sys

# Add parent directory to sys.path to enable module imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from coursework_one.a_pipeline.modules.db_loader.mongo_db import get_mongo_collection
from modules.extractors.pdf_tools import download_pdf, extract_text_from_pdf, clean_response
from modules.extractors.deepseek_extractor import query_deepseek_dynamic
from modules.storage.csv_writer import save_to_csv
from modules.storage.mongostore import initialize_indicators_database, save_indicators_to_mongo, reset_indicators_collection
from modules.utils.normalization import normalize_key, normalize_indicator_value
from modules.utils.validation import has_valid_indicator
from modules.utils.year_extraction import extract_year
from modules.utils.preprocessing import preprocess_text
from modules.report_availability.CSR_availability import check_csr_report
from modules.utils.standardization import standardize_unit_value
import json

CSR_DIR = "CSR_Reports"
os.makedirs(CSR_DIR, exist_ok=True)


def run_for_pdf_link(pdf_link, company_name="Test_Company"):
    """
    Process a PDF report from a given link and company name.

    Args:
        pdf_link (str): The URL of the PDF to download and process.
        company_name (str): The name of the company associated with the report.
    """
    reset_db = os.getenv("RESET_DB", "false").lower() == "true"

    if reset_db:
        print("⚡ RESET_DB is True → Resetting the indicators collection...")
        reset_indicators_collection()

    fake_report = {
        "pdf_link": pdf_link,
        "company_name": company_name
    }
    process_report(fake_report, reset_db=reset_db)


def process_report(report, reset_db=False):
    """
    Process a single report to extract indicators and save them to MongoDB and CSV.

    Args:
        report (dict): Report metadata containing at least 'pdf_link' and 'company_name'.
        reset_db (bool): Whether to reset the database before processing.
    """
    pdf_url = report.get("pdf_link")
    if not pdf_url:
        print("No PDF link found, skipping.")
        return

    company_name = report.get("company_name", "Unknown Company")
    company_name_filename = company_name.replace(" ", "_")

    pdf_filename = os.path.join(CSR_DIR, pdf_url.split("/")[-1].split("?")[0])

    # Download PDF if not already downloaded
    if not os.path.exists(pdf_filename):
        print(f"Downloading PDF for {company_name}...")
        download_pdf(pdf_url, pdf_filename)

    try:
        print(f"Extracting text from {pdf_filename}...")
        full_text, pages_text = extract_text_from_pdf(pdf_filename)
    except Exception as e:
        print(f"Failed to extract text from {pdf_filename}: {e}. Skipping this report.")
        return

    full_text = preprocess_text(full_text)

    # Try to extract report year from filename or text
    year = extract_year(pdf_filename)
    if not year:
        year = extract_year(full_text)

    if year:
        report_year = extract_year(year)
        if report_year:
            report_year = int(report_year)
            if not reset_db and check_csr_report(company_name, report_year):
                print(f"CSR report already exists for {company_name} ({report_year}). Skipping as already parsed.")
                return

    print("Querying DeepSeek...")
    responses = query_deepseek_dynamic(full_text, pages_text)

    valid_data = []
    for response_json in responses:
        try:
            cleaned_response = clean_response(response_json)
            valid_data.append(json.loads(cleaned_response))
        except Exception as e:
            print(f"Skipping invalid response: {e}")
            continue

    if not valid_data:
        print("No valid data extracted, skipping.")
        return

    merged_data = valid_data[-1]

    # Extract and normalize year from indicators or fallback
    if "year" in merged_data:
        merged_data["year"] = extract_year(merged_data["year"])

    for k, v in merged_data.items():
        if isinstance(v, dict) and "year" in v:
            v["year"] = extract_year(v["year"])

    year = merged_data.get("year")

    if not year:
        years = [v.get("year") for v in merged_data.values() if isinstance(v, dict) and v.get("year")]
        if years:
            from collections import Counter
            year = Counter(years).most_common(1)[0][0]
            print(f"Inferred year from indicators: {year}")
        else:
            filename_year = extract_year(pdf_filename)
            if filename_year:
                year = filename_year
                print(f"Falling back to year extracted from filename: {year}")
            else:
                print("No year found anywhere (indicators or filename), skipping.")
                return

    report_year = extract_year(year)
    if report_year:
        report_year = int(report_year)
    else:
        print(f"Could not extract valid year from '{year}', skipping.")
        return

    merged_data["year"] = report_year

    if not reset_db and check_csr_report(company_name, report_year):
        print(f"CSR report already exists for {company_name} ({report_year}). Skipping as already parsed.")
        return

    # Normalize indicator keys and values
    normalized_data = {}
    for k, v in merged_data.items():
        key_norm = normalize_key(k)

        if isinstance(v, dict) and "value" in v and "unit" in v:
            normalized_data[key_norm] = v
        elif isinstance(v, dict) and "value" in v:
            normalized_data[key_norm] = normalize_indicator_value(v["value"])
        elif isinstance(v, str):
            normalized_data[key_norm] = normalize_indicator_value(v)
        else:
            normalized_data[key_norm] = {"value": v, "unit": None}

    if not has_valid_indicator(normalized_data):
        print("No indicators found in extracted data, skipping save.")
        return

    indicators_in_data = [k for k, v in normalized_data.items() if isinstance(v, dict) and v.get("value") is not None]
    if not indicators_in_data:
        print("No indicators found in extracted data, skipping save.")
        return

    output_csv = f"output_{company_name_filename}_{report_year}.csv"
    save_to_csv(normalized_data, output_csv, company_name=company_name, pdf_link=pdf_url)
    print(f"Saved to CSV {output_csv}")

    # Define known indicators to check
    INDICATOR_KEYS = [
        "scope_1_emissions", "scope_2_emissions", "scope_3_emissions",
        "total_water_withdrawal", "total_water_consumption",
        "total_energy_consumption", "renewable_energy_consumption",
        "total_waste_generated", "hazardous_waste"
    ]

    indicators_list = []

    # Prepare list of valid indicators for MongoDB
    for key in INDICATOR_KEYS:
        value = normalized_data.get(key, {}).get("value")
        unit = normalized_data.get(key, {}).get("unit")

        if value is not None:
            std_value, std_unit = standardize_unit_value(value, unit)
            indicator_key = key.lower().replace(" ", "_")

            indicators_list.append({
                "indicator_key": indicator_key,
                "indicator_name": key.replace("_", " ").title(),
                "value": value,
                "unit": unit,
                "normalized_value": std_value,
                "normalized_unit": std_unit
            })

    if not indicators_list:
        print("No valid indicators found for this report → skipping save to MongoDB.")
        return

    indicators_collection = initialize_indicators_database()
    save_indicators_to_mongo(company_name, report_year, indicators_list, indicators_collection)
    print("Saved indicators to MongoDB.")


def main():
    """
    Main execution function to process all reports stored in MongoDB.
    Checks RESET_DB environment variable to optionally reset the collection.
    """
    reset_db = os.getenv("RESET_DB", "false").lower() == "true"

    if reset_db:
        print("RESET_DB is True → Resetting the indicators collection...")
        reset_indicators_collection()

    collection = get_mongo_collection()
    reports = collection.find({"pdf_link": {"$exists": True}})
    reports = list(reports)
    print(f"Found {len(reports)} reports.")

    for report in reports:
        process_report(report, reset_db=reset_db)


if __name__ == "__main__":
    # Optionally run for a hardcoded PDF link or run full pipeline
    main()
