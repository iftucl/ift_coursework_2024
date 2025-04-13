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

def check_memory_usage(threshold_percent=90):
    mem = psutil.virtual_memory()
    if mem.percent > threshold_percent:
        tqdm.write(f"⚠️ 内存使用过高：{mem.percent}%")
        return False
    return True

# === 子进程处理报告，并返回失败对象名（若有） ===
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
        tqdm.write(f"📥 下载：{object_name}")
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
        tqdm.write(f"❌ 处理文件失败：{object_name}，错误：{e}")
        return object_name  # 返回失败的对象名
    finally:
        if os.path.exists(local_file):
            os.remove(local_file)
        conn.close()

    return None  # 成功处理返回 None

def process_all_pdfs():
    conn_config = db_config

    with psycopg2.connect(**conn_config) as conn:
        indicators = load_indicators_from_db(conn)

    objects = list(minio_client.list_objects(MINIO_BUCKET, recursive=True))

    pool_size = 8
    batch_size = 80
    total_batches = (len(objects) + batch_size - 1) // batch_size

    tqdm.write(f"📊 总共需要处理 {len(objects)} 个文件，分为 {total_batches} 个 batch。")

    total_progress = tqdm(total=len(objects), desc="总体处理进度")
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

    total_progress.close()

    # 写入失败文件列表
    if failed_files:
        with open("failed_reports.json", "w", encoding="utf-8") as f:
            json.dump(failed_files, f, ensure_ascii=False, indent=2)
        tqdm.write(f"❗ 处理失败的文件已写入 failed_reports.json，共 {len(failed_files)} 个。")
    else:
        tqdm.write("🎉 所有文件处理成功，没有失败项。")

if __name__ == "__main__":
    process_all_pdfs()
