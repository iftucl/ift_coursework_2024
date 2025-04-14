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
import gc  # Import gc module for garbage collection

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

# === Modified: Use a generator to release PDF file resources ===
def extract_paragraphs_from_pdf(file_path):
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                clean_text = re.sub(r'\s+', ' ', text)
                splits = re.split(r'(?<=[。；.\n])\s*', clean_text)
                for para in splits:
                    if len(para.strip()) > 20:
                        yield (page.page_number, para.strip())  # Use yield to generate paragraphs on demand
    # pdfplumber automatically releases resources, no need to explicitly close pdf

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

# === New: Check if the same entry already exists ===
def check_if_entry_exists(conn, security, report_year, indicator_id):
    with conn.cursor() as cur:
        cur.execute("""
            SELECT 1 FROM csr_reporting.CSR_Data
            WHERE security = %s AND report_year = %s AND indicator_id = %s
            LIMIT 1
        """, (security, report_year, indicator_id))
        return cur.fetchone() is not None

def check_memory_usage(threshold_percent=90):
    mem = psutil.virtual_memory()
    if mem.percent > threshold_percent:
        tqdm.write(f"⚠️ Memory usage is too high: {mem.percent}%")
        return False
    return True

# === Process report in child processes and return failed object names (if any) ===
def process_report(args):
    from tqdm import tqdm
    conn_config, obj, indicators = args
    conn = psycopg2.connect(**conn_config)
    object_name = obj.object_name
    security, report_year = parse_security_and_year(object_name)
    if not security or not report_year:
        return object_name

    local_file = f"/tmp/{security}_{report_year}.pdf"
    try:
        tqdm.write(f"📥 Downloading: {object_name}")
        minio_client.fget_object(MINIO_BUCKET, object_name, local_file)

        paragraphs = extract_paragraphs_from_pdf(local_file)  # Using generator
        extraction_time = datetime.datetime.now()

        for indicator_id, indicator_name, keyword_list in indicators:
            # === Skip if already exists ===
            if check_if_entry_exists(conn, security, report_year, indicator_id):
                tqdm.write(f"⏭️ Skipping existing entry: {security} ({report_year}) - {indicator_name}")
                continue

            keywords = keyword_list or []
            matched = find_matching_paragraphs(paragraphs, keywords)
            if matched:
                tqdm.write(f"✅ Matched indicator【{indicator_name}】in {security} ({report_year}) - Paragraphs: {len(matched)}")
                insert_matched_data(conn, security, report_year, indicator_id, indicator_name, matched, extraction_time)

    except Exception as e:
        tqdm.write(f"❌ Failed to process file: {object_name}, Error: {e}")
        return object_name  # Return the failed object name
    finally:
        if os.path.exists(local_file):
            os.remove(local_file)
        conn.close()

    return None  # Return None if successfully processed

# === Perform garbage collection after each batch process ===
def process_all_pdfs():
    conn_config = db_config

    with psycopg2.connect(**conn_config) as conn:
        indicators = load_indicators_from_db(conn)

    objects = list(minio_client.list_objects(MINIO_BUCKET, recursive=True))

    pool_size = 10
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

        # Perform garbage collection after processing each batch
        gc.collect()

    total_progress.close()

    # Write the list of failed files
    if failed_files:
        with open("failed_reports.json", "w", encoding="utf-8") as f:
            json.dump(failed_files, f, ensure_ascii=False, indent=2)
        tqdm.write(f"❗ Failed files have been written to failed_reports.json, total of {len(failed_files)} files.")
    else:
        tqdm.write("🎉 All files processed successfully, no failures.")

if __name__ == "__main__":
    process_all_pdfs()
