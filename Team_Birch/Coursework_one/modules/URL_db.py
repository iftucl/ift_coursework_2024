import json
import re
import psycopg2
from pathlib import Path
import logging

# Logging setup
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

# File reference
BASE_DIR = Path(__file__).resolve().parent
INPUT_PATH = BASE_DIR / "db" / "company_pdf_links.json"

# Database credentials
DB_SETTINGS = {
    "dbname": "fift",
    "user": "postgres",
    "password": "postgres",
    "host": "localhost",
    "port": 5439
}

def parse_json(file_path):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as err:
        logger.error("Failed to parse JSON: %s", err)
        return {}

def connect_db():
    return psycopg2.connect(**DB_SETTINGS)

def get_symbol_for_name(cur, company):
    cur.execute(
        "SELECT symbol, security FROM csr_reporting.company_static WHERE security = %s",
        (company,)
    )
    return cur.fetchone()

def pull_year_from_url(link):
    patterns = [
        r"(\d{4})\.pdf$",
        r"_(\d{4})_",
        r"(\d{4})/[^/]+\.pdf$",
        r"([1-2][0-9]{3})"
    ]
    for p in patterns:
        m = re.search(p, link)
        if m:
            return int(m.group(1))
    return None

def process_entry(cur, name, links):
    record = get_symbol_for_name(cur, name)
    if not record:
        return
    symbol, _ = record
    for link in links:
        year = pull_year_from_url(link)
        cur.execute(
            """
            INSERT INTO csr_reporting.company_reports (symbol, security, report_url, report_year)
            VALUES (%s, %s, %s, %s)
            """,
            (symbol, name, link, year)
        )

def main():
    dataset = parse_json(INPUT_PATH)
    if not dataset:
        logger.warning("No data to process.")
        return

    try:
        conn = connect_db()
        cur = conn.cursor()

        for idx, (name, urls) in enumerate(dataset.items(), 1):
            logger.info("Processing [%d/%d]: %s", idx, len(dataset), name)
            process_entry(cur, name, urls)

        conn.commit()
        logger.info("Insertion completed.")
    except Exception as ex:
        logger.error("Execution failed: %s", ex)
    finally:
        if conn:
            cur.close()
            conn.close()

main()
