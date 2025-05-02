"""CSR Report Scraper – Team Magnolia
=====================================================================
High-level purpose
------------------
Collect global Corporate-Social-Responsibility (CSR) / ESG PDF reports for
hundreds of public companies, store the files in a MinIO **data-lake**, and
index the metadata in MongoDB so that it can be served by the FastAPI layer.

End-to-end flow
+---------------
1. **Company list** is read from *PostgreSQL* table `csr_reporting.company_static`
   (container `postgres_db_cw`).
2. For each company the scraper:
   a. Generates Google Custom-Search queries for every target year.
   b. Collects candidate URLs (direct PDFs and links on result pages) using
      *Selenium* if available, otherwise pure HTTP.
   c. Filters the links locally with keyword/regex heuristics.
   d. Sends the remaining list to **Groq LLM** which returns *one best URL per
      year* in JSON.
   e. Downloads each PDF using two-stage strategy: direct `requests` first,
      then Selenium/XHR fallback.
   f. Uploads successful downloads to MinIO bucket `csreport/{year}/…`.
   g. Upserts a metadata document into MongoDB collection `csr_db.csr_reports`.

Execution modes
+---------------
* **Docker-compose (recommended)** – container `magnolia_scraper_cw` already
  has `SELENIUM_URL` pointing at the stand-alone Selenium Grid. Nothing else
  needed:

    ```bash
    docker compose up -d           # start infra
    docker exec magnolia_scraper_cw poetry run python main.py scrape
    ```

* **Local development** – run Python on host, databases in Docker. Two
  options for Selenium:

  • Remote Grid → export `SELENIUM_URL=http://localhost:4444/wd/hub`
  • Local Chrome → pass `--local-selenium` CLI flag (sets
    `ALLOW_LOCAL_SELENIUM=true`).

    ```bash
    poetry run python main.py scrape --max-companies 20 --local-selenium
    ```

Parallelism
----------
Set `CSR_MAX_WORKERS` to 2-4 (hard-capped at 4) to enable ThreadPoolExecutor
for I/O-bound parallel scraping. Any value <2 falls back to sequential mode.

Important environment variables
-------------------------------
* `DOCKER_ENV`            – "true" inside the application container.
* `POSTGRES_HOST/PORT`    – override Postgres connection when not in Docker.
* `MONGO_URI`             – MongoDB connection string.
* `MINIO_HOST`            – host:port for MinIO.
* `SELENIUM_URL`          – (optional) Remote WebDriver endpoint.
* `ALLOW_LOCAL_SELENIUM`  – "true" to permit spawning a local Chrome.
* `CSR_MAX_WORKERS`       – number of parallel company workers (≤4).

Key public helpers
------------------
* `schedule_scraper()` – run the whole pipeline every 7 days with APScheduler.
* `main(max_companies)` – entry point used by `Team_Magnolia/coursework_one/main.py`.

File structure produced
----------------------
MinIO:

    csreport/
      └── {year}/
          └── {Company}.pdf

MongoDB (`csr_db.csr_reports`):

    {
      company_name:      str,
      csr_report_url:    str,   # original source URL
      storage_path:      str,   # MinIO object key
      csr_report_year:   int,
      ingestion_time:    ISO-8601 string
    }
"""
# CSR Scraper: Collects corporate sustainability reports from the web
# Imports standard libraries for file operations, timing, and date handling
import os
import sys
import time
import datetime
from urllib.parse import urljoin, urlparse
import json
import random
import re
import unicodedata
from typing import Dict, List, Optional, Set, Tuple, Any, IO
import tempfile

# Enables parallel processing of multiple companies
from concurrent.futures import ThreadPoolExecutor

# For HTTP requests to download PDFs
import requests
# Enables scheduled execution (e.g., weekly runs)
from apscheduler.schedulers.blocking import BlockingScheduler

# Web scraping tools using Selenium
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import WebDriverException, TimeoutException
from webdriver_manager.chrome import ChromeDriverManager

# Connects to PostgreSQL to retrieve the list of companies to scrape
import psycopg2

# Stores metadata about reports in MongoDB
from pymongo import MongoClient

# Stores actual PDF files in MinIO object storage
from minio import Minio

# Added for new finder logic
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from groq import Groq
from bs4 import BeautifulSoup

# Imports for downloader
import io # Added for downloader
import urllib3 # Added for downloader
from selenium.webdriver.remote.webdriver import WebDriver
from requests.adapters import HTTPAdapter # Added for downloader session
from urllib3.util.retry import Retry # Added for downloader session

# ========== Configuration area ==========
# PostgreSQL connection settings - source of company list
# Auto-detect if we're running in Docker or locally
if os.environ.get("DOCKER_ENV") == "true":
    # In Docker container - use container names
    DB_CONFIG = {
        "dbname": "fift",
        "user": "postgres",
        "password": "postgres",
        "host": os.environ.get("POSTGRES_HOST", "postgres_db"),
        "port": "5432",  # Inside Docker, no port forwarding
    }
else:
    # Local development - connect to Docker services via localhost
    DB_CONFIG = {
        "dbname": "fift",
        "user": "postgres",
        "password": "postgres",
        "host": os.environ.get("POSTGRES_HOST", "localhost"),
        "port": os.environ.get("POSTGRES_PORT", "5439"),  # Docker port forwarding
    }

# MongoDB connection for storing report metadata
# Auto-detect if we're running in Docker or locally
if os.environ.get("DOCKER_ENV") == "true":
    # In Docker container
    MONGO_URI = os.environ.get("MONGO_URI", "mongodb://mongo_db:27017")
else:
    # Local development
    MONGO_URI = os.environ.get("MONGO_URI", "mongodb://localhost:27019")

MONGO_DB_NAME = "csr_db"
MONGO_COLLECTION = "csr_reports"

mongo_client = MongoClient(MONGO_URI)
mongo_db = mongo_client[MONGO_DB_NAME]
collection_reports = mongo_db[MONGO_COLLECTION]

# MinIO connection for storing PDFs as objects
# Auto-detect if we're running in Docker or locally
if os.environ.get("DOCKER_ENV") == "true":
    # In Docker container
    MINIO_HOST = os.environ.get("MINIO_HOST", "miniocw:9000")
else:
    # Local development
    MINIO_HOST = os.environ.get("MINIO_HOST", "localhost:9000")

MINIO_CLIENT = Minio(
    MINIO_HOST,
    access_key="ift_bigdata",
    secret_key="minio_password",
    secure=False,
)
BUCKET_NAME = "csr-reports"

PROXY = None  

# ========== Logging functionality ==========
# Uses different log files depending on execution context
if "pytest" in sys.modules:
    LOG_FILE = "test_log.log"
else:
    LOG_FILE = "csr_fast.log"


def write_log(message: str):
    """
    Record logs to file and console.
    If in a pytest environment, writes to test_log.log;
    otherwise writes to csr_fast.log.
    """
    # Creates a timestamp for the log entry
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_msg = f"[{timestamp}] {message}"

    # Outputs log message to the console for immediate feedback
    print(log_msg)

    # Appends log message to the designated log file for later review
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(log_msg + "\n")


# ========== Core functionality ==========

# --- API Keys (Hardcoded from standalone script) ---
GROQ_API_KEY = "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"
GOOGLE_API_KEY = "AIzaSyCuU1JdIGqgLCYAWAALFm67ppXsLuIUd0I"
GOOGLE_SEARCH_ENGINE_ID = "a5faea352de5b417b"

# --- Search & Groq Settings
SEARCH_RESULTS_TO_PROCESS = 4
SEARCH_SCRAPE_DEPTH = 3
GROQ_MODEL_NAME = "deepseek-r1-distill-llama-70b" 
GROQ_MAX_LINKS_TO_SEND = 100
GROQ_MAX_RETRIES = 2
GROQ_RETRY_DELAY = 5

# --- Scraping & Download Settings
FINDER_PAGE_LOAD_TIMEOUT = 17 # Seconds for Selenium page load in finder
DOWNLOADER_PAGE_LOAD_TIMEOUT = 30 # Seconds for Selenium page load in downloader
REQUEST_TIMEOUT = 10 # Seconds for requests timeout
SELENIUM_SCRIPT_TIMEOUT = 20 # seconds for execute_async_script in downloader
FILE_SIZE_LIMIT = 100 * 1024 * 1024  # 100 MB limit (using 1024*1024 for MiB)
CHUNK_SIZE = 8192
HTTP_POOL_CONNECTIONS = 10
HTTP_POOL_MAXSIZE = 10
DOWNLOAD_RETRIES = 0 # Number of HTTP retries for direct download (0 = disabled)

# Selenium Chrome options for Finder/Scraper part
FINDER_CHROME_OPTIONS_ARGS = [
    "--headless=new", # Use new headless mode
    "--no-sandbox",
    "--disable-dev-shm-usage",
    "--disable-gpu",
    "--window-size=1920,1080",
    "--ignore-certificate-errors",
    "--disable-extensions",
    "--log-level=3",
    "--silent",
    # Use a common user agent to avoid bot detection
    "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
]

# Selenium Chrome options for Downloader part
DOWNLOADER_CHROME_OPTIONS_DICT = {
    "headless": True, 
    "no-sandbox": True,
    "disable-dev-shm-usage": True,
}

# Define User-Agent once globally
SHARED_USER_AGENT = random.choice([
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5.2 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/114.0",
])

# ------------------------------------------------------------------
# Selenium helpers (shared across finder & downloader)
# ------------------------------------------------------------------

def _use_remote_selenium() -> Optional[str]:
    """Return SELENIUM_URL (stripped) if provided, else None."""
    return os.getenv("SELENIUM_URL", "").strip() or None

# Allow opting into a local Selenium fallback explicitly when not using Docker
LOCAL_SELENIUM_ALLOWED = os.getenv("ALLOW_LOCAL_SELENIUM", "false").strip().lower() in {"true", "1", "yes"}

# --- Filtering Keywords (moved down after helper definitions) ---
PRIMARY_KEYWORDS = [
    "esg", "corporate", "social", "responsibility", "csr", "environment",
    "sustainability", "environmental", "impact", "responsible", "ss&i", "tcfd",
    "annual", "integrated", "governance", "climate",
]

EXCLUSION_KEYWORDS = [
    "press release", "news", "blog", "article", "careers", "jobs",
    "quarterly", "q1", "q2", "q3", "q4", "interim", "half-year", "investor relations",
    "linkedin", "facebook", "twitter", "instagram", "youtube",
    "#", ".html", ".htm", ".aspx", ".php", ".xml", ".zip", ".rar", ".7z", ".tar", ".gz",
    "press", "newsroom", "media", "shareholder", "proxy", "financial",
    "learn more", "slavery", "human trafficking", "modern slavery",
    "bond", "prospectus", "offering", "sec filing", "10-k", "form 20-f",
    "privacy policy", "terms of use", "cookie",
    "safety", "sds", "msds",
    "gender", "equal opportunity",
    "mailto:", "tel:",
    "response",
    "product", "products", "supplier", "customer",
    "jobs", "careers",
]

# --- Helper Functions ---

def _normalize_text(text: str) -> str:
    """Normalize Unicode text to NFKC form."""
    if not isinstance(text, str): return ""
    try:
        # NFKC attempts to normalize visually similar characters
        return unicodedata.normalize("NFKC", text)
    except Exception:
        return text # Return original if normalization fails

def _is_pdf_url(url: Optional[str]) -> bool:
    """Check if a URL likely points to a PDF """
    if not url:
        return False
    try:
        parsed_url = urlparse(url)
        path = parsed_url.path.lower()
        if path.endswith(".pdf"):
            return True
        # Check if 'pdf' is in the query part as well
        if 'pdf' in parsed_url.query.lower():
            return True
    except Exception:
        pass # Ignore parsing errors
    return False

def _extract_year(text: str) -> int:
    """Extract the most likely 4-digit year from text using multiple patterns (Reverted patterns)."""
    text = _normalize_text(text)
    # Patterns from standalone_report_finder2.py
    patterns = [
        r"(?:(?<![0-9_])|_)(20\d\d)(?=\b|[A-Za-z])", # YYYY (starting with 20)
        r"(20\d\d)[-_/](?:20\d\d)",                  # YYYY-YYYY (both starting with 20, extract first)
        r"(20\d\d)[-_/](?:\d\d)",                   # YYYY-YY (first starting with 20, extract first)
        r"FY[ -_]?(20\d\d)",                        # FY YYYY (starting with 20)
        r"FY[ -_]?(\d\d)",                         # FY YY (Will be converted to 20YY)
        r"(20\d\d)[-_/](20\d\d)",                    # Capture second year in YYYY-YYYY range (both 20xx)
        r"(20\d\d)[-_/](\d\d)"                     # Capture second year in YYYY-YY range (first 20xx)
    ]
    years_str = []
    for p in patterns:
        for match in re.findall(p, text): # Iterate through matches from findall
             # Flatten tuples from multiple capture groups, append strings
             years_str.extend(list(match)) if isinstance(match, tuple) else years_str.append(match)

    if not years_str: return 0

    current_year = datetime.datetime.now().year
    valid_years = set()
    for ys in filter(None, years_str):
        try:
            # Convert 2-digit years to 4-digit (assume 20xx), validate 4-digit
            y = int(ys) + 2000 if len(ys) == 2 else int(ys) if len(ys) == 4 else 0
            # Filter based on realistic range (e.g., 2000 to current year + 1)
            if 2000 <= y <= current_year + 1: valid_years.add(y)
        except ValueError: continue # Ignore strings that aren't valid integers

    # Return most recent valid year or 0
    return max(valid_years) if valid_years else 0


def _create_link(url: str, title: Optional[str] = None, label: Optional[str] = None, comment: Optional[str] = None) -> Dict[str, Any]:
    """Create a standardized link dictionary."""
    link_title = _normalize_text(title or url)
    link_label = _normalize_text(label or link_title)
    # Basic cleaning of label/title
    link_label = re.sub(r'\s+', ' ', link_label).strip()
    link_title = re.sub(r'\s+', ' ', link_title).strip()

    return {
        "url": url.strip(), # Ensure URL is stripped
        "title": link_title,
        "label": link_label,
        "comment": comment or "",
        "year": 0, # Placeholder
        "numerical_year": 0 # Placeholder
    }

# --- Google Custom Search Engine (CSE) ---
def _search_google_cse(query: str) -> List[Dict]:
    """Search Google Custom Search Engine (CSE)."""
    write_log(f"🔍 Searching Google CSE: {query}")
    standardized_results = []
    if not GOOGLE_API_KEY or not GOOGLE_SEARCH_ENGINE_ID:
        write_log("❌ ERROR: Google API Key or Search Engine ID not configured.")
        return []
    try:
        service = build("customsearch", "v1", developerKey=GOOGLE_API_KEY)
        res = service.cse().list(
            q=query,
            cx=GOOGLE_SEARCH_ENGINE_ID,
            num=SEARCH_RESULTS_TO_PROCESS
        ).execute()

        items = res.get('items', [])
        write_log(f"✅ Google CSE Search '{query}': {len(items)} results found.")

        for item in items:
            link = item.get('link')
            if link:
                standardized_results.append({
                    "url": link,
                    "title": item.get('title', link),
                    "body": item.get('snippet', '') # Use snippet as body
                })
    except HttpError as e:
        write_log(f"❌ Google CSE search failed for '{query}'. Error: {e}")
    except Exception as e:
        write_log(f"❌ An unexpected error occurred during Google CSE search for '{query}': {e}")

    return standardized_results


# --- Finder Logic ---
def find_reports_with_groq(company: str, start_year: int, end_year: int) -> Dict[int, str]:
    """
    Finds report URLs using Google CSE, scraping, filtering, and Groq analysis.
    Returns a dictionary mapping integer year to the best report URL string.
    """
    if not GROQ_API_KEY:
        write_log("❌ ERROR: GROQ_API_KEY not configured. Cannot perform Groq analysis.")
        return {}

    write_log(f"🚀 Starting Groq-based report search for '{company}' ({start_year}-{end_year})")

    # 1. Generate Search Queries
    search_queries = [f'"{company}" {year} Sustainability report'
                      for year in range(end_year, start_year - 1, -1)] # Search newest first

    write_log(f"🔎 Generated {len(search_queries)} search queries ")

    # 2. Execute Searches and Scrape Links
    all_raw_links: List[Dict] = []
    processed_urls_this_run: Set[str] = set()
    scraped_urls_in_run: Set[str] = set()

    # --- Selenium WebDriver Setup for Finder ---
    finder_driver = None
    options = ChromeOptions()
    options.add_argument(f"--user-agent={SHARED_USER_AGENT}") # Set user agent
    for arg in FINDER_CHROME_OPTIONS_ARGS:
        options.add_argument(arg)
    # Experimental options to make Selenium look less like automation
    options.add_experimental_option('excludeSwitches', ['enable-automation'])
    options.add_experimental_option('useAutomationExtension', False)
    options.add_argument("--disable-blink-features=AutomationControlled")

    selenium_url = _use_remote_selenium()

    try:
        if selenium_url:
            write_log(f"🔧 Initializing Remote Selenium WebDriver for Finder at {selenium_url}...")
            finder_driver = webdriver.Remote(
                command_executor=selenium_url,
                options=options
            )
        elif LOCAL_SELENIUM_ALLOWED:
            write_log("🔧 Initializing LOCAL Selenium WebDriver for link finding...")
            service = ChromeService(ChromeDriverManager().install())
            finder_driver = webdriver.Chrome(service=service, options=options)
        else:
            write_log("❌ Remote Selenium unavailable and local Selenium disabled → skipping Selenium step.")
            finder_driver = None

        if finder_driver:
            finder_driver.set_page_load_timeout(FINDER_PAGE_LOAD_TIMEOUT)
            write_log("✅ Finder WebDriver setup complete.")
    except (WebDriverException, Exception) as e:
        write_log(f"⚠️ WebDriver setup failed for finder: {e}. Scraping non-PDF links will be skipped.")
        finder_driver = None # Ensure driver is None if setup fails

    # --- Search and Scrape Loop ---
    onclick_pattern = re.compile(
        r"window\.location(?:\.href)?\s*=\s*['\"]([^'\"]+)['\"]|"
        r"window\.open\(['\"]([^'\"]+)['\"]"
    )

    for query in search_queries:
        results = _search_google_cse(query)
        if not results: continue

        scrape_counter = 0
        for result in results:
            url = result.get("url")
            if not url or url in processed_urls_this_run: continue

            processed_urls_this_run.add(url)
            title = result.get("title", url)

            if _is_pdf_url(url):
                write_log(f"🔗 Found potential direct PDF: {url}")
                all_raw_links.append(_create_link(url, title, comment="direct pdf from search"))
            elif finder_driver and scrape_counter < SEARCH_SCRAPE_DEPTH:
                scrape_counter += 1
                if url in scraped_urls_in_run:
                    # write_log(f"⏭️ Skipping already scraped URL: {url}")
                    continue

                write_log(f"📄 Scraping [Depth {scrape_counter}/{SEARCH_SCRAPE_DEPTH}]: {url}")
                try:
                    finder_driver.get(url)
                    WebDriverWait(finder_driver, FINDER_PAGE_LOAD_TIMEOUT / 2).until(
                        EC.presence_of_element_located((By.TAG_NAME, "body"))
                    )

                    current_url = finder_driver.current_url # Use current URL after potential redirects
                    link_elements = finder_driver.find_elements(By.CSS_SELECTOR, "a[href], [onclick]")
                    scraped_count = 0

                    for element in link_elements:
                        element_url: Optional[str] = None
                        element_label: str = ""
                        try:
                            element_label = element.text.strip() if element.text else ""
                            element_label = _normalize_text(element_label)

                            # 1. Check href attribute
                            href = element.get_attribute("href")
                            if href and href.strip() and not href.lower().startswith("javascript:"):
                                # Use urljoin from urllib.parse
                                element_url = urljoin(current_url, href.strip())

                            # 2. Check onclick if no valid href found
                            if not element_url:
                                onclick_js = element.get_attribute("onclick")
                                if onclick_js:
                                    matches = onclick_pattern.findall(onclick_js)
                                    for match in matches:
                                        possible_url = match[0] or match[1]
                                        if possible_url and possible_url.strip():
                                            # Use urljoin from urllib.parse
                                            element_url = urljoin(current_url, possible_url.strip())
                                            break # Take first valid URL

                            # 3. Add to list if a valid URL was found
                            if element_url and element_url not in processed_urls_this_run:
                                final_label = element_label or _normalize_text(element.get_attribute("title") or element_url)
                                all_raw_links.append(_create_link(element_url, final_label, comment=f"scraped from {url}"))
                                processed_urls_this_run.add(element_url)
                                scraped_count += 1

                        except Exception as link_err: # Catch errors processing a single element
                             pass # Continue with the next element

                    scraped_urls_in_run.add(url) # Mark original URL as scraped
                    write_log(f"    -> Scraped {scraped_count} new links from {current_url}")

                except (WebDriverException, TimeoutException, Exception) as scrape_err:
                    write_log(f"    -> ⚠️ Failed to scrape {url}: {scrape_err}")
                    # Add original URL as fallback if scraping failed
                    if url not in processed_urls_this_run:
                         all_raw_links.append(_create_link(url, title, comment="fallback - scraping failed"))
                         processed_urls_this_run.add(url)
            else:
                 # Match standalone logic: skip if not PDF and cannot scrape
                 # write_log(f"    -> Skipping non-PDF, cannot scrape: {url}") # Uncomment for debug
                 continue # Explicitly continue if not pdf and scraping conditions not met

    # --- Clean up Finder WebDriver ---
    if finder_driver:
        try:
            finder_driver.quit()
            write_log("✅ Finder WebDriver closed.")
        except Exception as e:
            write_log(f"⚠️ Error closing finder WebDriver: {e}")
    write_log(f"📊 Gathered {len(all_raw_links)} raw links for filtering.")

    # 3. Filter Links
    filtered_links = []
    processed_urls_for_filtering = set()
    all_raw_links.sort(key=lambda x: len(x.get("label", "")), reverse=True)

    min_report_year = start_year # Use start_year from function args

    for link in all_raw_links:
        url = link.get("url")
        if not url: continue

        url_lower = url.lower()
        if url_lower in processed_urls_for_filtering: continue

        label = link.get("label", "")
        title = link.get("title", "")
        comment = link.get("comment", "")
        combined_text = (label + " " + title + " " + url).lower() 

        # Relevance Check
        contains_primary = any(kw in combined_text for kw in PRIMARY_KEYWORDS)
        contains_exclusion = any(excl in combined_text for excl in EXCLUSION_KEYWORDS)
        is_pdf = _is_pdf_url(url)

        # Allow PDFs even if they contain exclusion keywords
        is_relevant = contains_primary and (not contains_exclusion or is_pdf)

        # Special case: Allow pdf links explicitly from the search
        if not is_relevant and comment == "direct pdf from search":
             if contains_primary:
                 is_relevant = True

        if not is_relevant:
            continue

        # Year Extraction and Filtering
        year = _extract_year(combined_text)
        numerical_year = 0
        year_str = "unknown"

        if year > 0:
            # Case 1: Year found in text
            if start_year <= year <= end_year:
                numerical_year = year
                year_str = str(year)
            else:
                continue # Skip if year found but outside requested range
        elif is_pdf and is_relevant:
            # Case 2: No year in text, but it IS a relevant PDF
            numerical_year = 0
            year_str = "unknown"
        else:
            # Case 3: No year found, and not a relevant PDF
            continue # Skip the link

        # Link seems relevant, add it
        link_dict = {
            "label": label if label != url else title,
            "url": url,
            "year": year_str,
            "numerical_year": numerical_year,
            "comment": comment
        }
        filtered_links.append(link_dict)
        processed_urls_for_filtering.add(url_lower)

    # Sort final list by year descending, unknown years at end
    filtered_links.sort(key=lambda x: (x.get('numerical_year', 0) == 0, -x.get('numerical_year', 0)))

    write_log(f"📊 Filtered down to {len(filtered_links)} potentially relevant links")

    # 4. Analyze with Groq
    if not filtered_links:
        write_log("⚠️ No relevant links found after filtering. Cannot proceed with Groq analysis.")
        return {}

    groq_client = Groq(api_key=GROQ_API_KEY)
    analysis_result_json = None

    links_to_send = filtered_links[:GROQ_MAX_LINKS_TO_SEND]
    write_log(f"🤖 Sending {len(links_to_send)} links to Groq ({GROQ_MODEL_NAME}) for analysis...")

    # Construct Prompts
    system_prompt = f"""You are a sustainability report expert. Identify the best \
sustainability report (or equivalent) url for {company} for each available year.

When analyzing, follow these steps:
1. Identify the year for each report.
2. For each year, select the single best report url considering:
   - Relevance: ESG/sustainability/environmental or equivalent report for {company}
   - Fallback: Use annual/integrated report if no dedicated sustainability report exists
   - Scope: Exclude regional or country-specific reports - only select global/company-wide reports
   - Format: Prefer PDF links over webpage links
   - Source: Prefer company sources over third-party domains.
   - IMPORTANT: Always use exact URLs as provided - do not edit, truncate or modify any URL
3. Return all years available in newest-to-oldest order.

Return *only* JSON format:
{{
  "yearly_reports": [
    {{
      "year": "YYYY",
      "url": "..."
    }}
  ]
}}
"""

    user_prompt_lines = []
    for idx, link in enumerate(links_to_send, start=1):
        year_info = f"(Estimated Year: {link.get('year', 'unknown')})"
        user_prompt_lines.append(f"{idx}. URL: {link['url']} {year_info} Label: {link.get('label', 'N/A')}")
    user_prompt = "Analyze the following URLs based on the system instructions and return the best report URL for each year:\n" + "\n".join(user_prompt_lines)

    # Log truncated user prompt
    log_user_prompt = (user_prompt[:1000] + '...' if len(user_prompt) > 1000 else user_prompt)
    write_log("\n--- Links Sent to Groq ---\n" + log_user_prompt + "\n--------------------------")

    # Call API with Retry
    for attempt in range(GROQ_MAX_RETRIES + 1):
        try:
            write_log(f"📞 Calling Groq API (Attempt {attempt + 1}/{GROQ_MAX_RETRIES+1})...")
            response = groq_client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                model=GROQ_MODEL_NAME,
                temperature=0.1, # Low temperature for factual extraction
                response_format={"type": "json_object"},
            )
            response_content = response.choices[0].message.content
            analysis_result_json = json.loads(response_content) # Store raw JSON

            # Validate structure
            if "yearly_reports" not in analysis_result_json or not isinstance(analysis_result_json["yearly_reports"], list):
                 raise ValueError("Groq response missing 'yearly_reports' list.")

            # Further validation of items in the list
            validated_reports = {}
            for item in analysis_result_json["yearly_reports"]:
                if isinstance(item, dict) and "year" in item and "url" in item:
                    try:
                        year_int = int(item["year"])
                        # Ensure URL is a non-empty string and seems valid
                        url_str = str(item["url"])
                        if start_year <= year_int <= end_year and url_str and urlparse(url_str).scheme in ('http', 'https'):
                            # Check if URL was actually in the list sent (prevent hallucination)
                            if any(sent_link['url'] == url_str for sent_link in links_to_send):
                                validated_reports[year_int] = url_str
                            else:
                                write_log(f"    -> ⚠️ Groq returned URL not in input list, discarding: {url_str}")
                        else:
                             write_log(f"    -> ⚠️ Groq returned invalid year/URL, discarding: Year {item.get('year')}, URL {item.get('url')}")
                    except (ValueError, TypeError):
                         write_log(f"    -> ⚠️ Groq returned invalid year format, discarding: {item.get('year')}")
                else:
                    write_log(f"    -> ⚠️ Groq returned invalid item format, discarding: {item}")

            if not validated_reports and analysis_result_json["yearly_reports"]:
                 write_log("    -> ⚠️ Groq returned data, but none passed validation.")

            write_log(f"✅ Groq analysis successful. Found validated reports for {len(validated_reports)} years.")
            return validated_reports # Return the validated dictionary {int_year: url_string}

        except json.JSONDecodeError as e:
             err_msg = f"Groq response was not valid JSON: {e}. Response: {response_content[:500]}"
        except (ValueError, TypeError) as e:
            err_msg = f"Groq response validation failed: {e}"
        except Exception as e: # Catch potential API errors from groq client
            err_msg = f"Groq API call failed: {type(e).__name__} - {e}"

        # Handle retry/failure
        if attempt < GROQ_MAX_RETRIES:
            write_log(f"    -> ⚠️ {err_msg}. Retrying in {GROQ_RETRY_DELAY}s...")
            time.sleep(GROQ_RETRY_DELAY)
        else:
            write_log(f"❌ Groq analysis failed after {GROQ_MAX_RETRIES + 1} attempts: {err_msg}")
            return {} # Return empty dict on final failure

    return {} # Should not be reached, but safety return


# --- Existing DB/Storage Functions ---

def upload_to_minio(company_name: str, year: int, local_path: str) -> Optional[str]:
    """Upload the PDF to MinIO, separated by year."""
    # Ensure year is int for path consistency
    object_name = f"{int(year)}/{company_name}.pdf"
    write_log(f"📤 Uploading {company_name}({year}) to MinIO as {object_name}...")
    try:
        with open(local_path, "rb") as file_data:
            file_stat = os.stat(local_path)
            MINIO_CLIENT.put_object(
                bucket_name=BUCKET_NAME,
                object_name=object_name,
                data=file_data,
                length=file_stat.st_size,
                content_type="application/pdf",
            )
        write_log(f"✅ Uploaded to MinIO successfully: {object_name}")
        return object_name
    except Exception as e:
        write_log(f"❌ Failed to upload '{local_path}' to MinIO: {type(e).__name__}, {e}")
        return None

def save_csr_report_info_to_mongo(company_name: str, pdf_url: str, object_name: str, year: int):
    """Save the CSR report information to MongoDB."""
    write_log(f"💾 Saving metadata to MongoDB for {company_name}({year})...")
    try:
        data = {
            "company_name": company_name,
            "csr_report_url": pdf_url, # The URL identified by Groq
            "storage_path": object_name, # Path in MinIO
            "csr_report_year": int(year), # Ensure year is int
            "ingestion_time": datetime.datetime.utcnow(),
        }
        # Use update_one with upsert=True to avoid duplicates on reruns
        update_result = mongo_db["csr_reports"].update_one(
            {"company_name": company_name, "csr_report_year": int(year)},
            {"$set": data},
            upsert=True,
        )
        if update_result.upserted_id:
            write_log(f"✅ MongoDB record inserted successfully: {company_name}({year})")
        elif update_result.modified_count > 0:
            write_log(f"✅ MongoDB record updated successfully: {company_name}({year})")
        else:
            write_log(f"ℹ️ MongoDB record already up-to-date: {company_name}({year})")

    except Exception as e:
        write_log(f"❌ Failed to update MongoDB record: {type(e).__name__}, {e}")


def get_company_list_from_postgres() -> List[str]:
    """Get the list of companies from PostgreSQL."""
    write_log("🔍 Connecting to PostgreSQL to read the company list...")
    try:
        # Connect to PostgreSQL using the configured credentials
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        # Query the company names from the company_static table
        cur.execute("SELECT security FROM csr_reporting.company_static;")
        rows = cur.fetchall()
        cur.close()
        conn.close()
        # Extract company names from query results
        companies = [row[0] for row in rows]
        write_log(f"✅ Retrieved {len(companies)} companies")
        return companies
    except Exception as e:
        # Handle database connection or query errors
        write_log(f"❌ Failed to read from PostgreSQL: {type(e).__name__}, {e}")
        return []


# --- Core Processing Logic ---

def search_and_process(company_name: str):
    """Finds, downloads, and stores CSR reports for a single company using new methods."""
    write_log(f"🚀 Starting processing for company: {company_name}")
    temp_pdf_dir = "./temp_pdfs" # Define temp dir
    os.makedirs(temp_pdf_dir, exist_ok=True) # Ensure temp dir exists

    try:
        start_year = 2020
        end_year = datetime.datetime.now().year # Use current year as end year dynamically
        write_log(f"📅 Target year range: {start_year}-{end_year}")

        # 1. Find reports using Groq-based finder
        # Returns dict { year_int: url_string }
        found_reports = find_reports_with_groq(company_name, start_year, end_year)

        if not found_reports:
            write_log(f"⚠️ No reports found by Groq for {company_name} in range {start_year}-{end_year}.")
            return # Exit processing for this company

        write_log(f"📄 Found {len(found_reports)} potential reports for {company_name}: {list(found_reports.keys())}")

        processed_count = 0
        # Sort years descending for processing
        for year in sorted(found_reports.keys(), reverse=True):
            url = found_reports[year]

            # 2. Check if already in MongoDB
            existing = mongo_db["csr_reports"].find_one(
                {"company_name": company_name, "csr_report_year": year}
            )
            if existing:
                write_log(f"⏭️ Skipping {company_name}({year}): Already exists in MongoDB (URL: {existing.get('csr_report_url')})")
                continue

            # 3. Download PDF Robustly
            write_log(f"⬇️ Attempting download for {company_name}({year}) from: {url}")
            pdf_bytes = download_pdf_robustly(url)

            if pdf_bytes:
                # 4. Save temporarily, Upload to MinIO, Save Metadata, Cleanup Temp
                temp_pdf_path = os.path.join(temp_pdf_dir, f"{company_name.replace(' ', '_')}_{year}_{random.randint(1000,9999)}.pdf")
                try:
                    write_log(f"💾 Saving temporary PDF to: {temp_pdf_path}")
                    with open(temp_pdf_path, "wb") as f:
                        f.write(pdf_bytes)

                    # 5. Upload to MinIO
                    obj_name = upload_to_minio(company_name, year, temp_pdf_path)

                    if obj_name:
                        # 6. Save metadata to MongoDB
                        save_csr_report_info_to_mongo(company_name, url, obj_name, year)
                        processed_count += 1
                    else:
                        write_log(f"❌ Failed to upload PDF to MinIO for {company_name}({year})")

                except IOError as e:
                     write_log(f"❌ Failed to write temporary PDF {temp_pdf_path}: {e}")
                except Exception as e:
                     write_log(f"❌ Unexpected error during upload/save for {company_name}({year}): {type(e).__name__} - {e}")
                finally:
                    # 7. Cleanup temp file
                    if os.path.exists(temp_pdf_path):
                        try:
                            os.remove(temp_pdf_path)
                            write_log(f"🗑️ Deleted temporary file: {temp_pdf_path}")
                        except OSError as e:
                            write_log(f"⚠️ Failed to delete temporary file {temp_pdf_path}: {e}")
            else:
                write_log(f"❌ Download failed for {company_name}({year}) from {url}")
            # Small delay between downloads for a company
            time.sleep(random.uniform(0.1, 0.5))

        if processed_count == 0 and found_reports:
             write_log(f"ℹ️ No *new* reports were downloaded and stored for {company_name} (already existed or downloads failed).")
        elif processed_count > 0:
             write_log(f"✅ Successfully processed {processed_count} new reports for {company_name}.")


    except Exception as e:
        write_log(f"❌ CRITICAL ERROR processing {company_name}: {type(e).__name__}, {e}")
    finally:
        # Clean up any remaining temp files for this company just in case
        try:
            if os.path.exists(temp_pdf_dir):
                for f in os.listdir(temp_pdf_dir):
                    if company_name.replace(' ', '_') in f:
                        os.remove(os.path.join(temp_pdf_dir, f))
        except Exception as cleanup_err:
            write_log(f"⚠️ Error during final temp file cleanup for {company_name}: {cleanup_err}")

# --- Batch Processing and Scheduling  ---

def process_batch(company_list: List[str]):
    """Process a batch of companies sequentially."""
    total_companies = len(company_list)

    # ---------------- Simple Worker Selection ----------------
    # Users can set CSR_MAX_WORKERS. If <2 → sequential. Cap at 4.
    max_workers = int(os.getenv("CSR_MAX_WORKERS", "1"))
    if max_workers < 2:
        write_log(f"🚀 Starting processing sequentially for {total_companies} companies…")
        for i, company_name in enumerate(company_list):
            write_log(f"🔄 Processing company {i+1}/{total_companies}: {company_name}")
            try:
                search_and_process(company_name)
                write_log(f"✅ Finished processing company {i+1}/{total_companies}: {company_name}")
            except Exception as e:
                write_log(f"❌❌❌ CRITICAL ERROR processing company {company_name} (at index {i}). Skipping. Error: {type(e).__name__} - {e}")
            time.sleep(random.uniform(0.5, 1.0))
    else:
        if max_workers > 4:
            write_log("⚠️ CSR_MAX_WORKERS capped at 4 to avoid resource issues.")
            max_workers = 4
        write_log(f"🚀 Starting batch processing for {total_companies} companies with {max_workers} workers…")
        # ThreadPoolExecutor for I/O-bound parallelism
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(search_and_process, comp): comp for comp in company_list}
            for i, future in enumerate(futures):
                comp_name = futures[future]
                try:
                    future.result()
                    write_log(f"✅ Finished processing company ({comp_name}) [{i+1}/{total_companies}]")
                except Exception as e:
                    write_log(f"❌❌❌ CRITICAL ERROR processing company {comp_name}. Error: {type(e).__name__} - {e}")

    write_log("🏁 Batch processing finished.")

def schedule_scraper():
    """Start a blocking scheduler that runs the main scraping logic every 7 days."""
    # Create a scheduler that blocks while running
    scheduler = BlockingScheduler()
    # Schedule the main function to run every week
    scheduler.add_job(main, "interval", days=7)
    write_log("⏳ Scraper scheduler started, running every 7 days...")

    try:
        # Start the scheduler (blocks until interrupted)
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        # Handle manual termination
        write_log("🛑 Scheduler stopped.")


def main(max_companies=None):
    """Run the CSR crawling process using the new finder/downloader."""
    write_log("📢 ==============================================")
    write_log("📢 Starting CSR Report Scraper (v2 - Groq/Robust Download)")
    write_log("📢 ==============================================")

    # Get the list of companies to process
    companies = get_company_list_from_postgres()
    if not companies:
        write_log("❌ No companies found in PostgreSQL. Exiting.")
        sys.exit(1)

    # Optionally limit the number of companies to process
    if max_companies:
        try:
            limit = int(max_companies)
            if limit > 0:
                companies = companies[:limit]
                write_log(f"ℹ️ Limiting processing to first {limit} companies.")
            else:
                write_log(f"⚠️ Invalid --max-companies value ({max_companies}). Processing all companies.")
        except ValueError:
            write_log(f"⚠️ Invalid --max-companies value ({max_companies}). Processing all companies.")

    # Create MinIO bucket if it doesn't exist )
    try:
        if not MINIO_CLIENT.bucket_exists(BUCKET_NAME):
            MINIO_CLIENT.make_bucket(BUCKET_NAME)
            write_log(f"✅ Created MinIO bucket: {BUCKET_NAME}")
        else:
            write_log(f"ℹ️ MinIO bucket '{BUCKET_NAME}' already exists.")
    except Exception as e:
         write_log(f"❌ Failed to check/create MinIO bucket: {e}. Exiting.")
         sys.exit(1)

    start_time = time.time()
    process_batch(companies)
    end_time = time.time()

    write_log(f"🎉 All companies processed in {end_time - start_time:.2f} seconds!")
    write_log("📢 ==============================================")


if __name__ == "__main__":
    # --- Argument Parsing (Optional limit) ---
    parser = argparse.ArgumentParser(description="Run the CSR Scraper.")
    parser.add_argument(
        "--max-companies",
        type=int,
        help="Limit the number of companies to process.",
        default=None
    )
    args = parser.parse_args()
    # --- End Argument Parsing ---

    main(max_companies=args.max_companies)

# --- Global HTTP Session for Direct Downloads ---
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Define retry strategy
DOWNLOADER_RETRY_CONFIG = Retry(
    total=DOWNLOAD_RETRIES,
    backoff_factor=0.5, # Add slight backoff if retries enabled
    status_forcelist=[500, 502, 503, 504], # Retry on server errors
    allowed_methods=["HEAD", "GET", "OPTIONS"] # Default retry methods
)

# Create a global session for direct downloads
DIRECT_DOWNLOAD_SESSION = requests.Session()
DIRECT_DOWNLOAD_SESSION.headers.update({"User-Agent": SHARED_USER_AGENT})
_adapter = HTTPAdapter(max_retries=DOWNLOADER_RETRY_CONFIG,
                       pool_connections=HTTP_POOL_CONNECTIONS,
                       pool_maxsize=HTTP_POOL_MAXSIZE)
DIRECT_DOWNLOAD_SESSION.mount("http://", _adapter)
DIRECT_DOWNLOAD_SESSION.mount("https://", _adapter)

# --- Downloader Helper Functions ---

def _get_parent_url(url: str) -> str:
    """Extract scheme and domain from a URL (e.g., https://example.com)."""
    try:
        parsed = urlparse(url)
        parent = f"{parsed.scheme}://{parsed.netloc}"
        return parent if parent != "://" else url # Handle cases with no scheme/netloc
    except Exception:
        write_log(f"⚠️ Could not parse parent URL from: {url}")
        return url # Fallback to original URL

def _is_valid_pdf_content(content: bytes) -> bool:
    """Check if byte content starts with the PDF magic header (%PDF)."""
    return content.startswith(b"%PDF")

def _create_browser_options_downloader() -> ChromeOptions:
    """Create ChromeOptions with required settings for the downloader."""
    options = ChromeOptions()
    # Set global User-Agent first
    options.add_argument(f"--user-agent={SHARED_USER_AGENT}")

    # Apply options from dictionary
    downloader_prefs = {}
    for option, value in DOWNLOADER_CHROME_OPTIONS_DICT.items():
        if option == "prefs" and isinstance(value, dict):
            downloader_prefs.update(value)
        elif isinstance(value, bool) and value:
            argument = f"--{option}" if option != "headless" else "--headless=new"
            options.add_argument(argument)
        elif isinstance(value, str):
            options.add_argument(f"--{option}={value}")

    # Set preferences
    if downloader_prefs:
        options.add_experimental_option("prefs", downloader_prefs)

    # Attempt to hide automation flags
    options.add_experimental_option('excludeSwitches', ['enable-automation'])
    options.add_experimental_option('useAutomationExtension', False)
    options.add_argument("--disable-blink-features=AutomationControlled")

    return options

def _get_webdriver_downloader() -> Optional[WebDriver]:
    """Create and return a Selenium WebDriver instance specifically for downloading.
       Connects to remote Selenium if DOCKER_ENV and SELENIUM_URL are set.
    """
    options = _create_browser_options_downloader()

    selenium_url = _use_remote_selenium()
    driver = None

    try:
        if selenium_url:
            write_log(f"🔧 Setting up Remote Selenium WebDriver for download fallback at {selenium_url}...")
            driver = webdriver.Remote(
                command_executor=selenium_url,
                options=options
            )
            write_log("✅ Downloader Remote WebDriver setup complete.")
        elif LOCAL_SELENIUM_ALLOWED:
            write_log("🔧 Setting up LOCAL Selenium WebDriver for download fallback...")
            service = ChromeService(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=options)
            write_log("✅ Downloader Local WebDriver setup complete.")
        else:
            write_log("❌ Remote Selenium unavailable and local Selenium disabled → skipping Selenium fallback.")
            return None

        if driver:
            driver.set_page_load_timeout(DOWNLOADER_PAGE_LOAD_TIMEOUT)
        return driver
        
    except Exception as e:
        write_log(f"❌ CRITICAL: Failed to initialize Downloader WebDriver: {e}")
        write_log("   Ensure Chrome/ChromeDriver or Selenium service is accessible and up-to-date.")
        # Ensure cleanup if partial failure
        if driver:
            try: driver.quit() 
            except: pass
        return None

def _navigate_to_url_downloader(driver: WebDriver, url: str) -> bool:
    """Navigate the Downloader WebDriver to the specified URL."""
    try:
        write_log(f"    -> Navigating downloader browser to: {url}")
        driver.get(url)
        # Basic check if page seems valid - presence of body tag
        WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        write_log(f"    -> Navigation successful (Title: {driver.title[:50]}...)")
        return True
    except TimeoutException:
        write_log(f"    -> ⚠️ Timeout navigating downloader browser to {url}")
        return False
    except WebDriverException as e:
        # Log concise WebDriver error
        err_line = str(e).split('\n')[0]
        write_log(f"    -> ⚠️ WebDriver error navigating downloader to {url}: {err_line}")
        return False
    except Exception as e:
        write_log(f"    -> ⚠️ Unexpected error navigating downloader to {url}: {type(e).__name__}")
        return False

# --- Core Download Functions ---

def _direct_download(url: str) -> Optional[bytes]:
    """Attempt to download the PDF using a direct HTTP GET request."""
    write_log(f"     T1: Attempting direct download: {url}")
    session = DIRECT_DOWNLOAD_SESSION # Use the global session
    try:
        extra_headers = {
            "Accept": "application/pdf,application/octet-stream,application/x-pdf,text/html;q=0.9,*/*;q=0.8",
            "Referer": _get_parent_url(url),
            "Accept-Encoding": "gzip, deflate", # Accept common encodings
            "Connection": "keep-alive",
        }
        resp = session.get(
            url,
            timeout=REQUEST_TIMEOUT,
            verify=False,
            stream=True,
            allow_redirects=True,
            headers=extra_headers
        )
        resp.raise_for_status() # Raise HTTPError for 4xx/5xx

        # Check content type
        content_type = resp.headers.get('Content-Type', '').lower()
        is_likely_pdf_content_type = 'pdf' in content_type or 'octet-stream' in content_type
        if not is_likely_pdf_content_type and 'html' in content_type:
             write_log(f"    -> ⚠️ Direct download check failed: Content-Type is HTML ({content_type})")
             return None
        if not is_likely_pdf_content_type:
             write_log(f"    -> ℹ️ Direct download Content-Type '{content_type}' not typical for PDF, proceeding with caution.")

        content = io.BytesIO()
        size = 0
        header_checked = False

        for chunk in resp.iter_content(chunk_size=CHUNK_SIZE):
            if not chunk: continue
            content.write(chunk)
            size += len(chunk)

            if not header_checked and size >= 4:
                if not _is_valid_pdf_content(content.getvalue()):
                    # Check if it looks like HTML
                    try:
                        decoded_start = content.getvalue()[:200].decode('utf-8', errors='ignore').lower()
                        if '<html' in decoded_start or '<body' in decoded_start or '<!doctype' in decoded_start:
                             raise ValueError("Downloaded content seems to be HTML, not PDF (magic number check)")
                    except UnicodeDecodeError:
                         pass # Not decodable as UTF-8, unlikely HTML
                    # If not clearly HTML but magic number wrong, fail
                    raise ValueError("Invalid PDF format detected (magic number mismatch)")
                header_checked = True

            if size > FILE_SIZE_LIMIT:
                raise ValueError(f"File exceeds size limit ({FILE_SIZE_LIMIT / (1024*1024):.1f} MiB)")

        # Final check for very small files
        if size > 0 and not header_checked:
             if not _is_valid_pdf_content(content.getvalue()):
                raise ValueError("Invalid PDF format detected (small file check)")

        pdf_bytes = content.getvalue()
        if not pdf_bytes:
            write_log("    -> ⚠️ Direct download resulted in empty content.")
            return None

        write_log(f"    -> ✅ Direct download successful: {len(pdf_bytes)/(1024*1024):.1f} MiB")
        return pdf_bytes

    except requests.exceptions.RequestException as e:
        # Log specific request errors concisely
        status_code = e.response.status_code if e.response is not None else "N/A"
        write_log(f"    -> ⚠️ Direct download failed (Request Error): {type(e).__name__}, Status: {status_code}")
        return None
    except ValueError as e:
        write_log(f"    -> ⚠️ Direct download failed (Validation Error): {e}")
        return None
    except Exception as e:
        write_log(f"    -> ⚠️ Direct download failed (Unexpected Error): {type(e).__name__} - {e}")
        return None

def _selenium_download(url: str) -> Optional[bytes]:
    """Attempt to download the PDF using Selenium and JavaScript XHR fallback."""
    write_log(f"    T2: Attempting Selenium XHR fallback: {url}")
    driver = _get_webdriver_downloader()
    if not driver:
        return None

    pdf_bytes = None
    try:
        if not _navigate_to_url_downloader(driver, url):
            # Navigation failed, no point trying XHR on this page
            raise ValueError("Selenium navigation failed, cannot execute XHR")

        current_url = driver.current_url
        page_title = driver.title
        # Basic check for error indicators on the navigated page
        if "404" in current_url or "error" in page_title.lower() or "not found" in page_title.lower():
             write_log(f"    -> ℹ️ Selenium navigated to potential error page: {current_url} (Title: {page_title})")
             # We still attempt XHR using the *original* URL

        download_url = url # Always use the original target URL for the XHR

        # JavaScript to download content via XHR, ensuring correct binary handling
        js_script = f"""
            var callback = arguments[arguments.length - 1];
            var xhr = new XMLHttpRequest();
            xhr.open('GET', arguments[0], true);
            xhr.responseType = 'arraybuffer'; // Request binary data

            xhr.onload = function() {{
                if (xhr.status === 200 || xhr.status === 206) {{
                    // Convert ArrayBuffer to Base64 for reliable transfer
                    var uInt8Array = new Uint8Array(xhr.response);
                    var binaryString = '';
                    for (var i = 0; i < uInt8Array.length; i++) {{
                        binaryString += String.fromCharCode(uInt8Array[i]);
                    }}
                    callback({{ success: true, data: btoa(binaryString) }}); // Send base64 encoded
                }} else {{
                    console.error('XHR failed. Status:', xhr.status, 'URL:', arguments[0]);
                    callback({{ error: 'XHR request failed', status: xhr.status }});
                }}
            }};

            xhr.onerror = function() {{
                console.error('XHR onerror triggered. URL:', arguments[0]);
                callback({{ error: 'XHR onerror triggered' }});
            }};

            xhr.timeout = {SELENIUM_SCRIPT_TIMEOUT} * 1000; // Timeout in milliseconds
            xhr.ontimeout = function () {{
                console.error('XHR request timed out. URL:', arguments[0]);
                callback({{ error: 'XHR request timed out' }});
            }};

            xhr.send();
        """

        driver.set_script_timeout(SELENIUM_SCRIPT_TIMEOUT + 1)

        write_log(f"    -> Executing XHR script for: {download_url}")
        result = driver.execute_async_script(js_script, download_url)

        if isinstance(result, dict) and 'error' in result:
             raise ValueError(f"JS XHR failed: {result.get('error')} (Status: {result.get('status', 'N/A')})")
        elif isinstance(result, dict) and result.get('success') and 'data' in result:
            # Decode Base64 data back to bytes
            import base64
            pdf_bytes = base64.b64decode(result['data'])
            write_log("    -> XHR script executed successfully, received data.")
        elif result is None:
             raise ValueError("JS XHR returned null (likely Selenium script timeout or JS issue)")
        else:
             raise ValueError(f"Unexpected JS XHR result: {str(result)[:100]}...")

        if not pdf_bytes:
             raise ValueError("Selenium download returned empty content after decoding.")

        # Validate downloaded content
        if not _is_valid_pdf_content(pdf_bytes):
            # Check if it might be HTML indicating an error/login page
            try:
                decoded_start = pdf_bytes[:200].decode('utf-8', errors='ignore').lower()
                if '<html' in decoded_start or '<body' in decoded_start or '<!doctype' in decoded_start:
                    raise ValueError("Downloaded content via Selenium is HTML, not PDF")
            except UnicodeDecodeError:
                 pass # Not decodable, unlikely HTML
            raise ValueError("Invalid PDF format from Selenium download (magic number check)")

        if len(pdf_bytes) > FILE_SIZE_LIMIT:
            raise ValueError(f"Selenium download exceeds size limit ({FILE_SIZE_LIMIT/(1024*1024):.1f} MiB)")

        write_log(f"    -> ✅ Selenium XHR download successful: {len(pdf_bytes)/(1024*1024):.1f} MiB")
        # pdf_bytes is already set correctly here

    except (WebDriverException, TimeoutException) as e:
        # Log concise WebDriver error
        err_line = str(e).split('\n')[0]
        write_log(f"    -> ⚠️ Selenium download failed (Browser Error): {type(e).__name__} - {err_line}")
        pdf_bytes = None
    except ValueError as e:
        write_log(f"    -> ⚠️ Selenium download failed (Validation/Script Error): {e}")
        pdf_bytes = None
    except Exception as e:
        write_log(f"    -> ⚠️ Selenium download failed (Unexpected Error): {type(e).__name__} - {e}")
        pdf_bytes = None
    finally:
        if driver:
            try:
                driver.quit()
                write_log("    -> ✅ Downloader WebDriver closed.")
            except Exception:
                 pass # Ignore errors during quit

    return pdf_bytes

def download_pdf_robustly(url: str) -> Optional[bytes]:
    """Main download function: tries direct HTTP, then falls back to Selenium/XHR."""
    # --- Strategy 1: Direct Download ---
    pdf_content = _direct_download(url)

    if pdf_content:
        return pdf_content
    else:
        # --- Strategy 2: Selenium Fallback ---
        write_log("    -> Direct download failed/invalid. Attempting Selenium fallback.")
        pdf_content = _selenium_download(url)
        if pdf_content:
            return pdf_content
        else:
            write_log(f"    -> ❌ Both direct and Selenium download methods failed for: {url}")
            return None
