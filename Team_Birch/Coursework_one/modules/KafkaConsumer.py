import io
import json
import logging
import requests
import psycopg2
from kafka import KafkaConsumer
from minio import Minio

from cw1_Birch.modules.KafkaProducer import DB_SETTINGS

# --- Setup ---
BROKER = 'localhost:9092'
TOPIC = 'csr-report'

DB_SETTINGS = {
    "host": "localhost",
    "port": 5439,
    "dbname": "fift",
    "user": "postgres",
    "password": "postgres"
}

MINIO_ENDPOINT = 'localhost:9000'
MINIO_KEY = 'ift_bigdata'
MINIO_SECRET = 'minio_password'
MINIO_BUCKET = 'csr-reports'

# --- Logging ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
log = logging.getLogger(__name__)

# --- Clients ---
minio_client = Minio(MINIO_ENDPOINT, access_key=MINIO_KEY, secret_key=MINIO_SECRET, secure=False)

consumer = KafkaConsumer(
    TOPIC,
    bootstrap_servers=[BROKER],
    value_deserializer=lambda v: json.loads(v.decode("utf-8"))
)

# --- Helpers ---

def init_db():
    try:
        return psycopg2.connect(**DB_SETTINGS)
    except Exception as err:
        log.error("Database init failed: %s", err)
        raise

def retrieve_pdf(url):
    try:
        resp = requests.get(url, timeout=60)
        if resp.status_code == 200:
            return resp.content
        raise Exception(f"HTTP {resp.status_code}")
    except Exception as ex:
        log.warning("Download failed (%s): %s", url, ex)
        raise

def store_to_minio(name, payload):
    buffer = io.BytesIO(payload)
    minio_client.put_object(
        MINIO_BUCKET,
        name,
        buffer,
        length=len(payload),
        content_type="application/pdf"
    )
    log.info("Uploaded: %s", name)

def update_record(cur, name, link):
    cur.execute(
        "UPDATE csr_reporting.company_reports SET minio_path = %s WHERE report_url = %s",
        (name, link)
    )

def handle_error(cur, link):
    cur.execute(
        "UPDATE csr_reporting.company_reports SET minio_path = %s WHERE report_url = %s",
        ("download_failed", link)
    )

def fetch_report_metadata(cur, url):
    cur.execute(
        "SELECT security, report_year FROM csr_reporting.company_reports WHERE report_url = %s",
        (url,)
    )
    return cur.fetchone()

def main():
    conn = init_db()
    cur = conn.cursor()

    log.info("Listening on topic: %s", TOPIC)
    for msg in consumer:
        data = msg.value
        name = data.get("company_name")
        links = data.get("report_urls", [])

        log.info("Company: %s (%d files)", name, len(links))
        for link in links:
            try:
                binary = retrieve_pdf(link)
                meta = fetch_report_metadata(cur, link)

                if not meta:
                    raise ValueError("No DB match for URL")

                symbol, year = meta
                target_name = f"{symbol}_{year}.pdf"
                store_to_minio(target_name, binary)
                update_record(cur, target_name, link)
                conn.commit()
            except Exception as err:
                log.error("Process failed for %s: %s", link, err)
                handle_error(cur, link)
                conn.commit()

    cur.close()
    conn.close()
    log.info("xyr complete.")

if __name__ == "__main__":
    main()
