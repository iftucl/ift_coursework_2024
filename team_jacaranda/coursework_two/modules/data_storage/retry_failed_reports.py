"""
This module is responsible for processing CSR (Corporate Social Responsibility) reports. 
It connects to a MinIO server to download the reports, extracts text paragraphs from 
PDF files, matches them against CSR indicators loaded from a PostgreSQL database, 
and stores the matched data back into the database.

The workflow includes the following key steps:
1. Downloading the CSR report from MinIO.
2. Extracting text paragraphs from the report's PDF file.
3. Matching the extracted paragraphs with predefined CSR indicators using fuzzy string matching.
4. Inserting matched data into the PostgreSQL database.
5. Supporting retry logic for processing failed reports.

Configuration:
- MinIO: Used for storing and retrieving CSR report PDF files.
- PostgreSQL: Used to store CSR indicators and matched data.

Dependencies:
- psycopg2: PostgreSQL database adapter.
- pdfplumber: PDF text extraction library.
- fuzzywuzzy: Fuzzy string matching library.
- tqdm: For progress bars.
- minio: MinIO Python client for object storage.
"""

import os
import json
import re
import datetime
import psycopg2
import pdfplumber
from minio import Minio
from fuzzywuzzy import fuzz
from pathlib import Path
from tqdm import tqdm

# === MinIO Configuration ===
MINIO_ENDPOINT = 'localhost:9000'
MINIO_ACCESS_KEY = 'ift_bigdata'
MINIO_SECRET_KEY = 'minio_password'
MINIO_BUCKET = 'csreport'

# === PostgreSQL Configuration ===
db_config = {
    "dbname": "fift",
    "user": "postgres",
    "password": "postgres",
    "host": "host.docker.internal",
    "port": 5439
}

# === Initialize MinIO Client ===
minio_client = Minio(
    MINIO_ENDPOINT,
    access_key=MINIO_ACCESS_KEY,
    secret_key=MINIO_SECRET_KEY,
    secure=False
)


def parse_security_and_year(object_name):
    """
    Parses the security identifier and report year from the given object name.

    This function expects the object name to follow a specific naming convention
    where the filename contains a security identifier followed by a 4-digit year
    (e.g., "ABC_2021.pdf").

    :param object_name: The name of the object (PDF file) stored in MinIO.
    :type object_name: str
    :return: A tuple containing the security identifier and report year,
             or (None, None) if parsing fails.
    :rtype: tuple or (None, None)
    """
    filename = Path(object_name).name
    match = re.match(r'(.+?)_(\d{4})\.pdf', filename, re.IGNORECASE)
    if match:
        return match.group(1), int(match.group(2))
    return None, None


def extract_paragraphs_from_pdf(file_path):
    """
    Extracts paragraphs from a PDF file.

    This function opens the specified PDF file, extracts the text from each page,
    and splits the text into paragraphs based on sentence delimiters. It only retains
    paragraphs with more than 20 characters.

    :param file_path: The path to the PDF file.
    :type file_path: str
    :return: A list of tuples, each containing the page number and a paragraph.
    :rtype: list of tuples (int, str)
    """
    paragraphs = []
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                clean_text = re.sub(r'\s+', ' ', text)
                splits = re.split(r'(?<=[。；.\n])\s*', clean_text)
                for para in splits:
                    if len(para.strip()) > 20:
                        paragraphs.append((page.page_number, para.strip()))
    return paragraphs


def find_matching_paragraphs(paragraphs, keywords, threshold=80):
    """
    Finds paragraphs that match the given keywords based on fuzzy string matching.

    This function compares each paragraph with the provided keywords using fuzzy
    string matching (via the fuzzywuzzy library) and returns the paragraphs with
    matches above a specified threshold.

    :param paragraphs: A list of paragraphs to search.
    :type paragraphs: list of tuples (int, str)
    :param keywords: A list of keywords to match against.
    :type keywords: list of str
    :param threshold: The minimum fuzzy match score to consider a paragraph as a match.
    :type threshold: int
    :return: A list of dictionaries containing the matched paragraphs with their page number.
    :rtype: list of dict
    """
    matched = []
    for page_num, para in paragraphs:
        match_count = sum(fuzz.partial_ratio(kw.lower(), para.lower()) >= threshold for kw in keywords)
        if match_count >= 2:
            matched.append({"page": page_num, "text": para})
    return matched


def load_indicators_from_db(conn):
    """
    Loads CSR indicators from the PostgreSQL database.

    This function queries the database for CSR indicator data, including indicator
    names and keywords, which are used later to match against extracted paragraphs.

    :param conn: The database connection object.
    :type conn: psycopg2.connection
    :return: A list of tuples containing indicator_id, indicator_name, and keywords.
    :rtype: list of tuples (int, str, list)
    """
    with conn.cursor() as cur:
        cur.execute("SELECT indicator_id, indicator_name, keywords FROM csr_reporting.CSR_indicators")
        return cur.fetchall()


def insert_matched_data(conn, security, report_year, indicator_id, indicator_name, matched, extraction_time):
    """
    Inserts the matched CSR data into the database.

    This function inserts the matched paragraphs along with metadata into the
    PostgreSQL database for later retrieval and reporting.

    :param conn: The database connection object.
    :type conn: psycopg2.connection
    :param security: The security identifier of the company.
    :type security: str
    :param report_year: The year of the CSR report.
    :type report_year: int
    :param indicator_id: The ID of the CSR indicator.
    :type indicator_id: int
    :param indicator_name: The name of the CSR indicator.
    :type indicator_name: str
    :param matched: A list of matched paragraphs.
    :type matched: list of dict
    :param extraction_time: The time when the data was extracted.
    :type extraction_time: datetime.datetime
    """
    with conn.cursor() as cur:
        cur.execute(""" 
            INSERT INTO csr_reporting.CSR_Data (
                security, report_year, indicator_id, indicator_name,
                source_excerpt, extraction_time
            )
            VALUES (%s, %s, %s, %s, %s::jsonb, %s)
        """, (
            security, report_year, indicator_id, indicator_name,
            json.dumps(matched), extraction_time
        ))
    conn.commit()


def process_single_report(object_name, indicators, conn_config):
    """
    Processes a single report by downloading it from MinIO, extracting paragraphs, 
    matching them with indicators, and saving the results to the database.

    This function downloads the report, extracts its paragraphs, matches them with
    CSR indicators, and stores the results in the database.

    :param object_name: The name of the object (PDF file) stored in MinIO.
    :type object_name: str
    :param indicators: A list of CSR indicators to match against.
    :type indicators: list of tuples (int, str, list)
    :param conn_config: The configuration for connecting to the PostgreSQL database.
    :type conn_config: dict
    :return: True if the report was processed successfully, False otherwise.
    :rtype: bool
    :raises Exception: If any error occurs during the processing of the report.
    """
    conn = psycopg2.connect(**conn_config)
    security, report_year = parse_security_and_year(object_name)
    if not security or not report_year:
        return False

    local_file = f"/tmp/{security}_{report_year}.pdf"
    try:
        tqdm.write(f"🔁 Retrying download: {object_name}")
        minio_client.fget_object(MINIO_BUCKET, object_name, local_file)
        paragraphs = extract_paragraphs_from_pdf(local_file)
        extraction_time = datetime.datetime.now()

        for indicator_id, indicator_name, keyword_list in indicators:
            keywords = keyword_list or []
            matched = find_matching_paragraphs(paragraphs, keywords)
            if matched:
                tqdm.write(f"✅ Matched indicator【{indicator_name}】in {security} ({report_year}) - Paragraphs: {len(matched)}")
                insert_matched_data(conn, security, report_year, indicator_id, indicator_name, matched, extraction_time)

    except Exception as e:
        tqdm.write(f"❌ Retry failed: {object_name}, Error: {e}")
        return False
    finally:
        if os.path.exists(local_file):
            os.remove(local_file)
        conn.close()

    return True


def retry_failed_reports():
    """
    Retries processing of reports that failed during a previous attempt. 
    If retrying fails, the report names are saved in the 'failed_reports.json' file.

    This function reads a list of failed report names from a JSON file, retries
    processing them, and updates the list of failed reports if necessary.

    :raises Exception: If any error occurs during the retry process.
    """
    script_dir = Path(__file__).parent
    failed_json_path = script_dir / "failed_reports.json"

    if not failed_json_path.exists():
        print("No failed_reports.json found, no need to retry.")
        return

    with open(failed_json_path, "r", encoding="utf-8") as f:
        failed_files = json.load(f)

    if not failed_files:
        print("failed_reports.json is empty, no need to retry.")
        return

    with psycopg2.connect(**db_config) as conn:
        indicators = load_indicators_from_db(conn)

    tqdm.write(f"🔄 Retrying processing of {len(failed_files)} failed files...")
    remaining_failed = []

    for object_name in tqdm(failed_files, desc="Retrying"):
        success = process_single_report(object_name, indicators, db_config)
        if not success:
            remaining_failed.append(object_name)

    if remaining_failed:
        with open(failed_json_path, "w", encoding="utf-8") as f:
            json.dump(remaining_failed, f, ensure_ascii=False, indent=2)
        tqdm.write(f"⚠️ {len(remaining_failed)} files still failed after retry, updated failed_reports.json.")
    else:
        failed_json_path.unlink()  # safer than os.remove
        tqdm.write("🎉 All failed files have been retried successfully, failed_reports.json has been cleared.")


if __name__ == "__main__":
    retry_failed_reports()
