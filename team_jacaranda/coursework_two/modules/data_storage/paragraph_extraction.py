"""
PDF Paragraph Extraction and CSR Indicator Matching Tool

This module provides functions to extract paragraphs from CSR reports in PDF format stored in MinIO,
match them against indicators stored in a PostgreSQL database, and store the matched results.

Modules used:
- MinIO for object storage access
- pdfplumber for PDF text extraction
- fuzzywuzzy for keyword similarity matching
- psycopg2 for PostgreSQL interaction
- tqdm for progress display
- multiprocessing for parallel processing
"""

import os
import re
import json
import datetime
import psycopg2
import pdfplumber
from minio import Minio
from fuzzywuzzy import fuzz
from pathlib import Path
from multiprocessing import Pool
from tqdm import tqdm
import psutil
import gc

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
    Parse the security identifier and report year from a given object name.

    :param object_name: The name of the PDF object in MinIO.
    :type object_name: str
    :return: Tuple of (security, year) or (None, None) if parsing fails.
    :rtype: tuple[str, int | None]
    """
    filename = Path(object_name).name
    match = re.match(r'(.+?)_(\d{4})\.pdf', filename, re.IGNORECASE)
    if match:
        return match.group(1), int(match.group(2))
    return None, None


def extract_paragraphs_from_pdf(file_path):
    """
    Extract paragraphs from a PDF file.

    :param file_path: Path to the local PDF file.
    :type file_path: str
    :yield: Tuple containing page number and cleaned paragraph text.
    :rtype: tuple[int, str]
    """
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                clean_text = re.sub(r'\s+', ' ', text)
                splits = re.split(r'(?<=[。；.\n])\s*', clean_text)
                for para in splits:
                    if len(para.strip()) > 20:
                        yield (page.page_number, para.strip())


def find_matching_paragraphs(paragraphs, keywords, threshold=80):
    """
    Find paragraphs that match a set of keywords using fuzzy string matching.

    :param paragraphs: List of (page number, paragraph) tuples.
    :type paragraphs: list[tuple[int, str]]
    :param keywords: List of keyword strings to match.
    :type keywords: list[str]
    :param threshold: Matching threshold (0–100), defaults to 80.
    :type threshold: int
    :return: List of matched paragraphs with page numbers.
    :rtype: list[dict]
    """
    matched = []
    for page_num, para in paragraphs:
        match_count = sum(fuzz.partial_ratio(kw.lower(), para.lower()) >= threshold for kw in keywords)
        if match_count >= 2:
            matched.append({"page": page_num, "text": para})
    return matched


def load_indicators_from_db(conn):
    """
    Load CSR indicators and associated keywords from the database.

    :param conn: PostgreSQL database connection.
    :type conn: psycopg2.connection
    :return: List of tuples (indicator_id, indicator_name, keywords).
    :rtype: list[tuple[int, str, list[str]]]
    """
    with conn.cursor() as cur:
        cur.execute("SELECT indicator_id, indicator_name, keywords FROM csr_reporting.CSR_indicators")
        return cur.fetchall()


def insert_matched_data(conn, security, report_year, indicator_id, indicator_name, matched, extraction_time):
    """
    Insert matched paragraphs into the csr_reporting.CSR_Data table.

    :param conn: PostgreSQL connection object.
    :type conn: psycopg2.connection
    :param security: Security identifier.
    :type security: str
    :param report_year: Year of the report.
    :type report_year: int
    :param indicator_id: ID of the matched indicator.
    :type indicator_id: int
    :param indicator_name: Name of the matched indicator.
    :type indicator_name: str
    :param matched: List of matched paragraph entries.
    :type matched: list[dict]
    :param extraction_time: Timestamp of extraction.
    :type extraction_time: datetime.datetime
    """
    with conn.cursor() as cur:
        cur.execute(""" 
            INSERT INTO csr_reporting.CSR_Data (
                security, report_year, indicator_id, indicator_name,
                source_excerpt, extraction_time
            )
            VALUES (%s, %s, %s, %s, %s::jsonb, %s)
            RETURNING data_id
        """, (
            security, report_year, indicator_id, indicator_name,
            json.dumps(matched), extraction_time
        ))
        data_id = cur.fetchone()[0]
        tqdm.write(f"🆗 Inserted data_id: {data_id}, security: {security}, year: {report_year}, indicator_id: {indicator_id}")
    conn.commit()


def check_memory_usage(threshold_percent=90):
    """
    Check current memory usage and print a warning if it exceeds a given threshold.

    :param threshold_percent: Memory usage percentage threshold.
    :type threshold_percent: int
    :return: True if memory usage is below threshold, else False.
    :rtype: bool
    """
    mem = psutil.virtual_memory()
    if mem.percent > threshold_percent:
        tqdm.write(f"⚠️ Memory usage is too high: {mem.percent}%")
        return False
    return True


def process_report(args):
    """
    Process a single PDF report: download, extract, match indicators, and insert data.

    :param args: Tuple of (conn_config, MinIO object, indicators).
    :type args: tuple
    :return: Object name if failed, else None.
    :rtype: str | None
    """
    from tqdm import tqdm
    conn_config, obj, indicators = args
    conn = psycopg2.connect(**conn_config)
    object_name = obj.object_name
    security, report_year = parse_security_and_year(object_name)
    if not security or not report_year:
        return object_name

    local_file = f"/tmp/{security}_{report_year}.pdf"
    not_matched_count = 0
    matched_count = 0
    try:
        tqdm.write(f"📥 Downloading: {object_name}")
        minio_client.fget_object(MINIO_BUCKET, object_name, local_file)

        paragraphs = list(extract_paragraphs_from_pdf(local_file))
        extraction_time = datetime.datetime.now()

        for indicator_id, indicator_name, keyword_list in indicators:
            keywords = keyword_list
            matched = find_matching_paragraphs(paragraphs, keywords)
            if matched:
                matched_count += 1
                tqdm.write(f"✅ Matched indicator【{indicator_name}】in {security} ({report_year}) - Paragraphs: {len(matched)}")
                insert_matched_data(conn, security, report_year, indicator_id, indicator_name, matched, extraction_time)
            else:
                not_matched_count += 1

        tqdm.write(f"📄 Finished processing {object_name}: {matched_count} matched indicators, {not_matched_count} not matched.")

    except Exception as e:
        tqdm.write(f"❌ Failed to process file: {object_name}, Error: {e}")
        return object_name
    finally:
        if os.path.exists(local_file):
            os.remove(local_file)
        conn.close()

    return None


def process_all_pdfs():
    """
    Main pipeline to process all PDF files from MinIO:
    - Downloads each file
    - Extracts paragraphs
    - Matches with indicators
    - Saves matched results to the database
    - Logs failed files
    """
    conn_config = db_config

    with psycopg2.connect(**conn_config) as conn:
        indicators = load_indicators_from_db(conn)

    objects = list(minio_client.list_objects(MINIO_BUCKET, recursive=True))

    pool_size = 5
    batch_size = 50
    total_batches = (len(objects) + batch_size - 1) // batch_size

    tqdm.write(f"📊 A total of {len(objects)} files need to be processed, divided into {total_batches} batches.")

    total_progress = tqdm(total=len(objects), desc="Overall progress")
    failed_files = []

    for i in range(0, len(objects), batch_size):
        batch = objects[i:i+batch_size]
        with Pool(pool_size) as pool:
            for result in pool.imap_unordered(
                process_report, [(conn_config, obj, indicators) for obj in batch]
            ):
                total_progress.update(1)
                if result:
                    failed_files.append(result)

        gc.collect()

    total_progress.close()

    script_dir = Path(__file__).parent
    failed_json_path = script_dir / "failed_reports.json"

    if failed_files:
        with open(failed_json_path, "w", encoding="utf-8") as f:
            json.dump(failed_files, f, ensure_ascii=False, indent=2)
        tqdm.write(f"❗ Failed files have been written to {failed_json_path}, total of {len(failed_files)} files.")
    else:
        tqdm.write("🎉 All files processed successfully, no failures.")


if __name__ == "__main__":
    process_all_pdfs()
