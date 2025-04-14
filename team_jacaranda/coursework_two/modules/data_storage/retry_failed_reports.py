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
    filename = Path(object_name).name
    match = re.match(r'(.+?)_(\d{4})\.pdf', filename, re.IGNORECASE)
    if match:
        return match.group(1), int(match.group(2))
    return None, None

def extract_paragraphs_from_pdf(file_path):
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
    matched = []
    for page_num, para in paragraphs:
        match_count = sum(fuzz.partial_ratio(kw.lower(), para.lower()) >= threshold for kw in keywords)
        if match_count >= 2:
            matched.append({"page": page_num, "text": para})
    return matched

def load_indicators_from_db(conn):
    with conn.cursor() as cur:
        cur.execute("SELECT indicator_id, indicator_name, keywords FROM csr_reporting.CSR_indicators")
        return cur.fetchall()

def insert_matched_data(conn, security, report_year, indicator_id, indicator_name, matched, extraction_time):
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
    if not os.path.exists("failed_reports.json"):
        print("No failed_reports.json found, no need to retry.")
        return

    with open("failed_reports.json", "r", encoding="utf-8") as f:
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
        with open("failed_reports.json", "w", encoding="utf-8") as f:
            json.dump(remaining_failed, f, ensure_ascii=False, indent=2)
        tqdm.write(f"⚠️ {len(remaining_failed)} files still failed after retry, updated failed_reports.json.")
    else:
        os.remove("failed_reports.json")
        tqdm.write("🎉 All failed files have been retried successfully, failed_reports.json has been cleared.")

if __name__ == "__main__":
    retry_failed_reports()
