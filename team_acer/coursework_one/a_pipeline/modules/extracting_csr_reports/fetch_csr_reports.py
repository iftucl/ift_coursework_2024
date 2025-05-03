import os
import time
import re
import psycopg2
import requests
import pdfplumber
import urllib.parse
from datetime import datetime
from googleapiclient.discovery import build
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup

from ..minio_writer.store_minio import ensure_minio_bucket, check_minio_exists, upload_to_minio
from ..postgres_writer.store_postgres import check_if_report_exists, store_metadata_in_postgres, create_csr_metadata_table_if_not_exists, store_indicators_in_postgres, create_csr_indicators_table_if_not_exists, indicators_exist
from ..indicators.indicator_extractors import IndicatorExtractor
# =============================
#        CONFIGURATION
# =============================

def _init_(self, name, age):
    self.name = name
    self.age = age

# PostgreSQL Database Configuration
DB_HOST = "localhost"
DB_PORT = "5439"
DB_NAME = "fift"
DB_USER = "postgres"
DB_PASSWORD = "postgres"

current_year = datetime.now().year
API_KEY = "AIzaSyBAOTC3Qit-XYxlvuLbAJ5fyapdhUyENHk"
CSE_ID = "2285ebcd503434ee7"
PDF_SAVE_DIR = "downloaded_reports"
os.makedirs(PDF_SAVE_DIR, exist_ok=True)

# =============================
#   CHECK IF REPORT EXISTS
# =============================

def report_already_exists(region, country, sector, industry, symbol, year):
    """Check if CSR report exists in PostgreSQL or MinIO."""
    return check_if_report_exists(symbol, year) or check_minio_exists(region, country, sector, industry, symbol, year)

# =============================
#   RETRIEVE COMPANIES
# =============================

def get_companies_from_db():
    """Retrieve company list from PostgreSQL."""
    try:
        with psycopg2.connect(host=DB_HOST, port=DB_PORT, dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD) as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT symbol, security, region, country, gics_sector, gics_industry FROM csr_reporting.company_static")
                companies = cursor.fetchall()
        return companies if companies else []
    except psycopg2.Error as e:
        print(f"❌ PostgreSQL Connection Error: {e}")
        return []


# =============================
#   GOOGLE SEARCH WITH BACKOFF
# =============================

def google_search(security, year, num_results=5):
    """Use Google API to search for CSR reports globally with more query variations."""
    queries = [
        f'"{security} ESG/CSR sustainability report {year}" filetype:pdf',
        f"{security} {year} ESG report filetype:pdf",
        f'"{security} {year} ESG report" OR "{security} {year} sustainability report" filetype:pdf'
    ]

    service = build("customsearch", "v1", developerKey=API_KEY)
    backoff_time = 2  # Start with 2 seconds

    for query in queries:
        try:
            print(f"🔍 Searching Google API: {query}")
            res = service.cse().list(q=query, cx=CSE_ID, num=num_results).execute()
            pdf_links = [item.get("link") for item in res.get("items", []) if item.get("link", "").endswith(".pdf")]

            if pdf_links:
                print(f"✅ Found {len(pdf_links)} reports for {security} ({year})")
                return pdf_links
        
        except Exception as e:
            if "rateLimitExceeded" in str(e):
                print(f"⚠️ Google API Rate Limit Exceeded. Retrying in {backoff_time} seconds...")
                time.sleep(backoff_time)
                backoff_time *= 2  # Exponential backoff
                continue
            print(f"⚠️ Google API Error: {e}")
            return []

    return []

# =============================
#   BACKUP SCRAPER (RESPONSIBILITYREPORTS.COM)
# =============================

def scrape_company_website(security, year):
    """Scrape the company's official website for sustainability reports."""
    search_url = f"https://www.google.com/search?q={security}+{year}+sustainability+report+filetype:pdf"

    try:
        response = requests.get(search_url, headers={"User-Agent": "Mozilla/5.0"})
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        pdf_links = [a["href"] for a in soup.find_all("a", href=True) if "pdf" in a["href"]]
        return pdf_links[0] if pdf_links else None
    except requests.exceptions.RequestException as e:
        print(f"⚠️ Scraping Error: {e}")

    return None

# =============================
#   EXTRACT YEAR FROM URL
# =============================

def extract_year_from_url(url):
    """Extracts the year from the URL using regex (only 2020-2029)."""
    patterns = [
        r'[^0-9](202[0-9])[^0-9]',  # Matches 2020-2029 with non-numeric boundaries
        r'(?:report|_|-|/)(202[0-9])(?:_|-|/)',
    ]
    for pattern in patterns:
        match = re.search(pattern, url, re.IGNORECASE)
        if match:
            return int(match.group(1))
    return None

# =============================
#   VALIDATE REPORT (CHECK YEAR & CONTENT)
# =============================

def validate_report(file_path, expected_security, expected_year):
    """
    Validates a CSR report by checking:
    - Expected (shortened) name and year on early pages.
    - CSR/ESG/Sustainability keywords.
    - PDF metadata or strong report header detection.
    """

    print(f"🔍 Validating: {file_path} for {expected_security} ({expected_year})")

    # Use only the first word of the company name for relaxed matching
    short_name = expected_security.split()[0].lower()

    keywords = [
        "sustainability report", "csr report", "esg report",
        "corporate responsibility report", "non-financial report",
        "environmental social governance", "corporate social responsibility",
        "sustainability", "corporate responsibility", "impact report",
        "sustainability review"
    ]

    try:
        with pdfplumber.open(file_path) as pdf:
            # --- 1. Metadata Title ---
            meta_title = pdf.metadata.get("Title", "") or ""
            if short_name in meta_title.lower() and str(expected_year) in meta_title:
                print("✅ Matched in PDF metadata title")
                return True

            # --- 2. First 5 pages ---
            for i in range(min(5, len(pdf.pages))):
                text = pdf.pages[i].extract_text()
                if not text:
                    continue
                lower_text = text.lower()

                has_name = short_name in lower_text
                has_year = str(expected_year) in lower_text
                has_csr_kw = any(kw in lower_text for kw in keywords)

                strong_header = re.search(
                    r"(sustainability|csr|esg|non-financial|responsibility|impact)[\s\-:]*report[\s\-:]*20[0-9]{2}",
                    lower_text
                )

                if has_name and has_year and (has_csr_kw or strong_header):
                    print(f"✅ Matched on page {i+1} with CSR indicators and name '{short_name}'")
                    return True

            print("❌ Failed robust validation: CSR content or company name/year not found.")
            return False

    except Exception as e:
        print(f"❌ Error while validating report: {e}")
        return False
    
# =============================
#   DOWNLOAD PDF (BEST VERSION)
# =============================

def download_pdf(pdf_url, security, year):
    """
    Downloads a PDF and saves it locally.
    Returns: File path of downloaded PDF or None if download fails.
    """
    file_name = f"{security}_{year}.pdf".replace(" ", "_")  # Clean file name
    file_path = os.path.join(PDF_SAVE_DIR, file_name)

    try:
        response = requests.get(pdf_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
        
        # ✅ Raise error for non-200 responses (e.g., 404, 500)
        response.raise_for_status()

        # ✅ Save PDF
        with open(file_path, "wb") as f:
            f.write(response.content)

        print(f"✅ Successfully Downloaded: {file_path}")
        return file_path

    except requests.exceptions.HTTPError as http_err:
        print(f"❌ HTTP Error: {http_err} | URL: {pdf_url}")

    except requests.exceptions.ConnectionError:
        print(f"❌ Connection Error. Failed to reach {pdf_url}")

    except requests.exceptions.Timeout:
        print(f"❌ Timeout Error. {pdf_url} took too long to respond.")

    except requests.exceptions.RequestException as e:
        print(f"❌ Download Failed: {pdf_url} | Error: {e}")

    return None  # Return None if download fails

# =============================
#   PROCESS SINGLE COMPANY
# =============================

def process_company(symbol, security, region, country, sector, industry):
    """Process a single company and fetch CSR reports year by year."""
    for year in range(2020, current_year):
        print(f"🔄 Processing {security} ({year})...")

        if report_already_exists(region, country, sector, industry, symbol, year):
            if indicators_exist(symbol, year):
                print(f"✅ Report and indicators already exist for {security} ({year}), skipping.")
                continue

            print(f"🟡 Report exists for {security} ({year}), but indicators are missing. Re-extracting...")

            # Attempt to load the saved report from downloaded_reports
            file_path = f"downloaded_reports/{security.replace(' ', '_')}_{year}.pdf"
            if not os.path.exists(file_path):
                print(f"⚠️ Local copy not found: {file_path}")
                print(f"❌ Skipping {security} ({year}) — local report needed to extract indicators.")
                continue

            extractor = IndicatorExtractor(file_path)
            indicators = extractor.extract_all(country=country)

            store_indicators_in_postgres(
                symbol, security, year, region, country, sector, industry,
                water_con=indicators["water"].get("standardised_mcm"),
                donation_amt=indicators["donation"].get("donation"),
                waste_gen=indicators["waste"].get("standardised_mt"),
                renewable_mwh=indicators["renewable"].get("amount"),
                renewable_pct=indicators["renewable"].get("percentage"),
                air_emissions_nox=indicators["air"].get("nox"),
                air_emissions_sox=indicators["air"].get("sox"),
                air_emissions_voc=indicators["air"].get("voc"),
            )

            print(f"✅ Re-extracted and stored missing indicators for {security} ({year})")
            continue  # ✅ Skip full scraping pipeline for this year

        # ------------------------
        # Normal scraping pipeline
        # ------------------------
        pdf_links = google_search(security, year)
        if not pdf_links:
            print(f"⚠️ Google API failed, using backup scraper for {security} ({year})...")
            pdf_links = [scrape_company_website(security, year)]

        if not pdf_links or not pdf_links[0]:
            print(f"❌ No reports found for {security} ({year}). Moving to next year.")
            time.sleep(5)
            continue

        for pdf_url in pdf_links[:5]:
            detected_year = extract_year_from_url(pdf_url) or year
            file_path = download_pdf(pdf_url, security, detected_year)

            if file_path and validate_report(file_path, security, detected_year):
                minio_url = upload_to_minio(file_path, region, country, sector, industry, security, detected_year)
                if minio_url:
                    store_metadata_in_postgres(symbol, security, detected_year, region, country, sector, industry, minio_url)

                    extractor = IndicatorExtractor(file_path)
                    indicators = extractor.extract_all(country=country, target_year=year)

                    store_indicators_in_postgres(
                        symbol, security, detected_year, region, country, sector, industry,
                        scope1=indicators["scope"].get("scope_1"),
                        scope2=indicators["scope"].get("scope_2"),
                        scope3=indicators["scope"].get("scope_3"),
                        total_emissions=indicators["scope"].get("total_emissions"),
                        water_con=indicators["water"].get("standardised_mcm"),
                        currency=indicators.get("currency"),
                        donation_amt=indicators["donation"].get("donation"),
                        waste_gen=indicators["waste"].get("standardised_mt"),
                        renewable_mwh=indicators["renewable"].get("standardised_mwh"),
                        renewable_pct=indicators["renewable"].get("percentage"),
                        air_emissions_nox=indicators["air"].get("standardised_nox"),
                        air_emissions_sox=indicators["air"].get("standardised_sox"),
                        air_emissions_voc=indicators["air"].get("standardised_voc")
                    )

                    print(f"✅ Stored indicators for {security} ({detected_year}) in PostgreSQL.")
                    os.remove(file_path)
                    print(f"🧹 Deleted local copy of {security} ({detected_year})")
                    break

        time.sleep(5)

# =============================
#   MAIN FUNCTION
# =============================

def fetch_csr_reports():
    """Fetch CSR reports one company at a time, one year at a time."""
    ensure_minio_bucket()
    create_csr_metadata_table_if_not_exists()
    create_csr_indicators_table_if_not_exists()
    companies = get_companies_from_db()
    for company in companies:
        process_company(*company)

if __name__ == "__main__":
    fetch_csr_reports()