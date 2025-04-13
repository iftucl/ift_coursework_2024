import os
import logging
import psycopg2
import requests
from tqdm import tqdm
from minio import Minio
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

# --- PostgreSQL 配置 ---
db_config = {
    "dbname": "fift",
    "user": "postgres",
    "password": "postgres",
    "host": "host.docker.internal",
    "port": 5439
}

# --- MinIO 配置 ---
MINIO_ENDPOINT = 'localhost:9000'
MINIO_ACCESS_KEY = 'ift_bigdata'
MINIO_SECRET_KEY = 'minio_password'
MINIO_BUCKET = 'csreport'

# --- 初始化 MinIO 客户端 ---
minio_client = Minio(
    MINIO_ENDPOINT,
    access_key=MINIO_ACCESS_KEY,
    secret_key=MINIO_SECRET_KEY,
    secure=False
)

# 创建桶（如果不存在）
if not minio_client.bucket_exists(MINIO_BUCKET):
    minio_client.make_bucket(MINIO_BUCKET)

# --- 日志设置 ---
log_dir = Path("./logs")
log_dir.mkdir(exist_ok=True)

logging.basicConfig(
    filename=log_dir / "upload_reports.log",
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

# --- 本地下载目录 ---
download_dir = Path("./downloaded_reports")
download_dir.mkdir(parents=True, exist_ok=True)

# --- 记录失败链接 ---
failed_urls_path = log_dir / "failed_urls.txt"

# --- 单个下载+上传任务 ---
def download_and_upload(security, url, year):
    try:
        # 下载 PDF
        response = requests.get(url, timeout=15)
        response.raise_for_status()

        filename = f"{security}_{year or 'unknown'}.pdf"
        local_path = download_dir / filename

        # 保存文件
        with open(local_path, "wb") as f:
            f.write(response.content)

        # 上传到 MinIO
        object_name = f"{security}/{filename}"
        minio_client.fput_object(
            bucket_name=MINIO_BUCKET,
            object_name=object_name,
            file_path=str(local_path),
            content_type="application/pdf"
        )

        # 删除本地文件
        os.remove(local_path)

        # 上传成功后，更新 MinIO 路径到 PostgreSQL
        update_minio_path(security, year, object_name)

        logging.info(f"✅ Uploaded: {object_name}")
        return True

    except Exception as e:
        logging.error(f"❌ Failed: {url} | Security: {security} | Year: {year} | Reason: {e}")
        with open(failed_urls_path, "a") as fail_log:
            fail_log.write(f"{security}\t{year}\t{url}\n")  # ✅ 记录失败信息
        return False

# --- 更新 MinIO 路径到 PostgreSQL ---
def update_minio_path(security, report_year, object_name):
    try:
        # 连接 PostgreSQL 数据库
        conn = psycopg2.connect(**db_config)
        cursor = conn.cursor()

        # 使用 security 和 report_year 更新 minio_path
        update_query = """
        UPDATE csr_reporting.company_reports
        SET minio_path = %s
        WHERE security = %s AND report_year = %s
        """
        cursor.execute(update_query, (object_name, security, report_year))

        conn.commit()
        cursor.close()
        conn.close()

        logging.info(f"✅ Updated MinIO path for {security} (Year: {report_year}) to {object_name}")

    except Exception as e:
        logging.error(f"❌ Failed to update MinIO path for {security} (Year: {report_year}): {e}")

# --- 主函数 ---
def main():
    try:
        conn = psycopg2.connect(**db_config)
        cursor = conn.cursor()

        cursor.execute("SELECT security, report_url, report_year FROM csr_reporting.company_reports")
        records = cursor.fetchall()

        # 使用线程池并发处理
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [
                executor.submit(download_and_upload, security, url, year)
                for security, url, year in records
            ]

            for _ in tqdm(as_completed(futures), total=len(futures), desc="Concurrent Uploads"):
                pass

    except Exception as db_error:
        logging.critical(f"Database error: {db_error}")
    finally:
        if conn:
            cursor.close()
            conn.close()

if __name__ == "__main__":
    main()
