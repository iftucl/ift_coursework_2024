import os
import logging
import requests
from minio import Minio
from pathlib import Path
import psycopg2
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm

# --- 日志设置 ---
log_dir = Path("./logs")
log_dir.mkdir(exist_ok=True)

logging.basicConfig(
    filename=log_dir / "retry_upload_reports.log",
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

# --- MinIO 配置 ---
MINIO_ENDPOINT = 'localhost:9000'
MINIO_ACCESS_KEY = 'ift_bigdata'
MINIO_SECRET_KEY = 'minio_password'
MINIO_BUCKET = 'csreport'

# --- PostgreSQL 配置 ---
db_config = {
    "dbname": "fift",
    "user": "postgres",
    "password": "postgres",
    "host": "host.docker.internal",
    "port": 5439
}

# --- 初始化 MinIO 客户端 ---
minio_client = Minio(
    MINIO_ENDPOINT,
    access_key=MINIO_ACCESS_KEY,
    secret_key=MINIO_SECRET_KEY,
    secure=False
)

# --- 失败链接文件路径 ---
failed_urls_path = log_dir / "failed_urls.txt"

# --- 本地下载目录 ---
download_dir = Path("./downloaded_reports")
download_dir.mkdir(parents=True, exist_ok=True)

# --- 更新 MinIO 路径到 PostgreSQL ---
def update_minio_path(security, report_year, object_name):
    try:
        conn = psycopg2.connect(**db_config)
        cursor = conn.cursor()
        update_query = """
        UPDATE csr_reporting.company_reports
        SET minio_path = %s
        WHERE security = %s AND report_year = %s
        """
        cursor.execute(update_query, (object_name, security, report_year))
        conn.commit()
        cursor.close()
        conn.close()
        logging.info(f"✅ Updated MinIO path for {security} ({report_year})")
    except Exception as e:
        logging.error(f"❌ DB Update failed for {security} ({report_year}): {e}")

# --- 单个下载 + 上传任务 ---
def download_and_upload(security, url, year):
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()

        filename = f"{security}_{year}.pdf"
        local_path = download_dir / filename

        # 保存文件
        with open(local_path, "wb") as f:
            f.write(response.content)

        object_name = f"{security}/{filename}"

        # 上传到 MinIO
        minio_client.fput_object(
            bucket_name=MINIO_BUCKET,
            object_name=object_name,
            file_path=str(local_path),
            content_type="application/pdf"
        )

        # 删除本地文件
        os.remove(local_path)

        # 更新数据库
        update_minio_path(security, year, object_name)

        logging.info(f"✅ Uploaded: {object_name}")
        return True

    except Exception as e:
        logging.error(f"❌ Failed: {url} | {security} | {year} | Reason: {e}")
        return False

# --- 重试函数 ---
def retry_failed_urls():
    if not failed_urls_path.exists():
        logging.info("No failed_urls.txt file found.")
        return

    with open(failed_urls_path, "r") as f:
        lines = [line.strip() for line in f.readlines() if line.strip()]

    retry_entries = []
    for line in lines:
        parts = line.split('\t')
        if len(parts) == 3:
            security, year_str, url = parts
            try:
                year = int(year_str)
                retry_entries.append((security, year, url))
            except ValueError:
                logging.warning(f"⚠️ Skipped malformed line (invalid year): {line}")
        else:
            logging.warning(f"⚠️ Skipped malformed line: {line}")

    remaining_failed = []

    with ThreadPoolExecutor(max_workers=10) as executor:
        future_to_entry = {
            executor.submit(download_and_upload, security, url, year): (security, year, url)
            for security, year, url in retry_entries
        }

        for future in tqdm(as_completed(future_to_entry), total=len(future_to_entry), desc="Retrying Failed Uploads"):
            security, year, url = future_to_entry[future]
            try:
                success = future.result()
                if not success:
                    remaining_failed.append(f"{security}\t{year}\t{url}\n")
            except Exception as e:
                logging.error(f"❌ Exception in retry thread: {url} | {e}")
                remaining_failed.append(f"{security}\t{year}\t{url}\n")

    # 重新写回剩余失败项
    with open(failed_urls_path, "w") as f:
        f.writelines(remaining_failed)

    logging.info(f"✅ Retry completed. Remaining failed: {len(remaining_failed)}")

# --- 主程序入口 ---
if __name__ == "__main__":
    retry_failed_urls()
