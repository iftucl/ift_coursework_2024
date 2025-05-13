import os
import time
import json
import logging
import sqlite3
import requests
from pathlib import Path
from bs4 import BeautifulSoup
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter
from googleapiclient.discovery import build
from googleapiclient.discovery_cache.base import Cache

# ------------------ Configuration ------------------

API_KEY = "AIzaSyDGsGcYPX8S1YiQFh5BVkwBeEvom_OicGs"
CSE_ID = "f1f78e0820d794e53"
BASE = "https://www.responsibilityreports.com"
DB_FILE = Path(__file__).resolve().parents[2] / "Equity.db"
#DB_FILE = "./Equity.db"
OUTPUT = Path(__file__).resolve().parent / "db/company_pdf_links.json"

# ------------------ Logging ------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)
log = logging.getLogger(__name__)

# ------------------ Google API Cache ------------------

class InMemoryCache(Cache):
    _store = {}
    def get(self, url): return self._store.get(url)
    def set(self, url, content): self._store[url] = content

# ------------------ HTTP Session ------------------

def init_http():
    s = requests.Session()
    retries = Retry(total=5, backoff_factor=0.4, status_forcelist=[500, 502, 503, 504])
    s.mount("https://", HTTPAdapter(max_retries=retries))
    return s

http = init_http()

# ------------------ Core Utilities ------------------

def sanitize(name: str, as_corp=False) -> str:
    n = name.lower()
    n = n.replace("corp.", "corporation").replace("corp ", "corporation ")
    n = n.replace("corp-", "corporation-")
    if as_corp:
        n = n.replace("company", "corporation")
    return n.replace(" ", "-").replace(".", "")

def load_companies(db_path: str) -> list[str]:
    if not Path(db_path).exists():
        log.warning("Database not found: %s", db_path)
        return []
    try:
        with sqlite3.connect(db_path) as conn:
            cur = conn.cursor()
            cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='equity_static'")
            if not cur.fetchone():
                return []
            cur.execute("SELECT security FROM equity_static")
            return [row[0] for row in cur.fetchall()]
    except Exception as e:
        log.error("DB read failed: %s", str(e))
        return []

def fetch_from_site(name: str, alt=False):
    path = sanitize(name, as_corp=alt)
    url = f"{BASE}/Company/{path}"
    log.info("Requesting: %s", url)
    try:
        r = http.get(url, timeout=10)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        links = set()
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if href.lower().endswith(".pdf"):
                full = BASE + href if not href.startswith("http") else href
                links.add(full.strip().rstrip("/"))
        return list(links) if links else None
    except Exception as ex:
        log.warning("Site search failed: %s", str(ex))
        return None

def is_acceptable(link: str, title=""):
    return "annual" not in link.lower() and "annual" not in title.lower()

def google_pdf_search(company: str):
    log.info("Google API query initiated for: %s", company)
    results = set()
    try:
        service = build("customsearch", "v1", developerKey=API_KEY, cache=InMemoryCache())
        for y in range(2013, 2024):
            q = f"{company} {y} responsibility report sustainability report filetype:pdf"
            try:
                res = service.cse().list(q=q, cx=CSE_ID, num=10).execute()
                for item in res.get("items", []):
                    link = item.get("link", "").strip().rstrip("/")
                    title = item.get("title", "")
                    if link.lower().endswith(".pdf") and is_acceptable(link, title):
                        results.add(link)
                        break
                time.sleep(1)
            except Exception as e:
                log.warning("Google search failed: %s", str(e))
                if "quota" in str(e).lower():
                    break
    except Exception as ex:
        log.error("Google service setup failed: %s", str(ex))
    return list(results)

def retrieve_links(name: str):
    log.info("Searching reports for: %s", name)
    r1 = fetch_from_site(name)
    if r1: return r1
    if "company" in name.lower():
        r2 = fetch_from_site(name, alt=True)
        if r2: return r2
    return google_pdf_search(name)

def read_results() -> dict:
    if OUTPUT.exists():
        try:
            with open(OUTPUT, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}
    return {}

def write_results(data: dict):
    try:
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        with open(OUTPUT, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        log.error("Failed to write results: %s", str(e))

# ------------------ Main Execution ------------------

def main():
    companies = load_companies(DB_FILE)
    if not companies:
        log.error("No company data found.")
        return

    log.info("Loaded %d companies", len(companies))
    data = read_results()

    for idx, name in enumerate(companies, 1):
        log.info("[%d/%d] Processing: %s", idx, len(companies), name)
        if name in data:
            log.info("Already processed: %s", name)
            continue
        found = retrieve_links(name)
        data[name] = found
        write_results(data)
        time.sleep(1)

    log.info("Completed all processing.")

if __name__ == "__main__":
    main()
