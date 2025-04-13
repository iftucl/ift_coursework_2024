import os
import json
import datetime
import psycopg2
import pdfplumber
from minio import Minio
from fuzzywuzzy import fuzz
from pathlib import Path
from tqdm import tqdm

# === MinIO 配置 ===
MINIO_ENDPOINT = 'localhost:9000'
MINIO_ACCESS_KEY = 'ift_bigdata'
MINIO_SECRET_KEY = 'minio_password'
MINIO_BUCKET = 'csreport'

# === PostgreSQL 配置 ===
db_config = {
    "dbname": "fift",
    "user": "postgres",
    "password": "postgres",
    "host": "host.docker.internal",
    "port": 5439
}

# === 初始化 MinIO 客户端 ===
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
        tqdm.write(f"🔁 重试下载：{object_name}")
        minio_client.fget_object(MINIO_BUCKET, object_name, local_file)
        paragraphs = extract_paragraphs_from_pdf(local_file)
        extraction_time = datetime.datetime.now()

        for indicator_id, indicator_name, keyword_list in indicators:
            keywords = keyword_list or []
            matched = find_matching_paragraphs(paragraphs, keywords)
            if matched:
                tqdm.write(f"✅ 匹配到指标【{indicator_name}】在 {security} ({report_year}) - 段落数: {len(matched)}")
                insert_matched_data(conn, security, report_year, indicator_id, indicator_name, matched, extraction_time)

    except Exception as e:
        tqdm.write(f"❌ 重试失败：{object_name}，错误：{e}")
        return False
    finally:
        if os.path.exists(local_file):
            os.remove(local_file)
        conn.close()

    return True

def retry_failed_reports():
    if not os.path.exists("failed_reports.json"):
        print("未找到 failed_reports.json，无需重试。")
        return

    with open("failed_reports.json", "r", encoding="utf-8") as f:
        failed_files = json.load(f)

    if not failed_files:
        print("failed_reports.json 是空的，无需重试。")
        return

    with psycopg2.connect(**db_config) as conn:
        indicators = load_indicators_from_db(conn)

    tqdm.write(f"🔄 正在重试处理 {len(failed_files)} 个失败文件...")
    remaining_failed = []

    for object_name in tqdm(failed_files, desc="重试中"):
        success = process_single_report(object_name, indicators, db_config)
        if not success:
            remaining_failed.append(object_name)

    if remaining_failed:
        with open("failed_reports.json", "w", encoding="utf-8") as f:
            json.dump(remaining_failed, f, ensure_ascii=False, indent=2)
        tqdm.write(f"⚠️ 重试后仍有 {len(remaining_failed)} 个文件处理失败，已更新 failed_reports.json。")
    else:
        os.remove("failed_reports.json")
        tqdm.write("🎉 所有失败文件重试成功，已清空 failed_reports.json。")

if __name__ == "__main__":
    retry_failed_reports()
