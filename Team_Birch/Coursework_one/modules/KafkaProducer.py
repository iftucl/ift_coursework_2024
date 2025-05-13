import json
import psycopg2
import logging
from kafka import KafkaProducer

# --- Configuration ---
BROKER = 'localhost:9092'
TOPIC = 'csr-report'

DB_SETTINGS = {
    "host": "localhost",
    "port": 5439,
    "dbname": "fift",
    "user": "postgres",
    "password": "postgres"
}

# --- Logger ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
log = logging.getLogger(__name__)

# --- Kafka Init ---
producer = KafkaProducer(
    bootstrap_servers=[BROKER],
    value_serializer=lambda v: json.dumps(v).encode("utf-8")
)

# --- Database Access ---
def get_conn():
    try:
        return psycopg2.connect(**DB_SETTINGS)
    except Exception as err:
        log.error("DB connection failed: %s", err)
        raise

def retrieve_data(cur):
    try:
        sql = """
        SELECT cs.security, cr.report_url
        FROM csr_reporting.company_reports cr
        JOIN csr_reporting.company_static cs ON cr.security = cs.security
        """
        cur.execute(sql)
        return cur.fetchall()
    except Exception as err:
        log.error("Query failed: %s", err)
        raise

def bundle_by_company(rows):
    pool = {}
    for name, link in rows:
        pool.setdefault(name, []).append(link)
    return pool

def publish_msg(company, urls):
    msg = {
        "company_name": company,
        "report_urls": urls
    }
    log.info("Dispatching: %s", company)
    producer.send(TOPIC, value=msg)
    producer.flush()

# --- Main Routine ---
def run():
    conn = get_conn()
    try:
        cur = conn.cursor()
        records = retrieve_data(cur)
        grouped = bundle_by_company(records)
        for key, urls in grouped.items():
            publish_msg(key, urls)
    finally:
        conn.close()
        log.info("All tasks completed.")

run()
