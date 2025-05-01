import os
import logging
import time
import sys
import random
import re
import hashlib
import threading
from typing import Set, List, Dict, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
import datetime
from io import BytesIO

import requests
import pdfplumber
from minio import Minio
from minio.error import S3Error
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

# Import Postgres management class
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "..", "..", "..", "..", ".."))
sys.path.append(project_root)

from team_wisteria.coursework_one.a_pipeline.modules.url_parser.database import PostgresManager

# ---------------------------------------------
#              Configuration Area
# ---------------------------------------------
class Config:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    REPORTS_DIR = os.path.join(BASE_DIR, "reports")
    LOGS_DIR = os.path.join(BASE_DIR, "logs")

    MAX_WORKERS = 5
    BROWSER_TIMEOUT = 60
    REQUEST_TIMEOUT = 60
    RETRY_DELAY = (1, 3)
    MAX_RETRIES = 3

    PDF_MIN_LENGTH = 1000
    VALID_KEYWORDS = {"sustainability", "esg", "csr", "environment", "social"}

    USER_AGENTS = [
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
    ]

    COMPANY_LIST_URL = "https://www.responsibilityreports.com/Companies?searchTerm="

    # MinIO 设置
    MINIO_ENDPOINT = "localhost:9000"
    MINIO_ACCESS_KEY = "ift_bigdata"
    MINIO_SECRET_KEY = "minio_password"
    MINIO_BUCKET = "report1"

# ---------------------------------------------
#         Initialize logs and directories
# ---------------------------------------------
os.makedirs(Config.REPORTS_DIR, exist_ok=True)
os.makedirs(Config.LOGS_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(Config.LOGS_DIR, 'crawler.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ---------------------------------------------
#        ResponsibilityReportsScraper
# ---------------------------------------------
class ResponsibilityReportsScraper:
    """
Grab all company links from responsibilityreports.com.
Scan all the tags for each company page, filter out candidate PDF links,
Download and store to MinIO and Postgres, keep the filename consistent。
    """

    def __init__(self):
        self.lock = threading.Lock()
        self.seen_urls: Set[str] = set()
        self.seen_hashes: Set[str] = set()
        self.current_user_agent = random.choice(Config.USER_AGENTS)
        self.driver_pool = []

        # Initialize MinIO client
        self.minio_client = Minio(
            Config.MINIO_ENDPOINT,
            access_key=Config.MINIO_ACCESS_KEY,
            secret_key=Config.MINIO_SECRET_KEY,
            secure=False
        )
        # Initialize the Postgres manager
        self.pg_manager = PostgresManager(
            host="localhost", port=5439, user="postgres", password="postgres"
        )

    def init_driver(self) -> webdriver.Chrome:
        options = webdriver.ChromeOptions()
        options.add_argument('--headless')
        options.add_argument(f'--user-agent={self.current_user_agent}')
        service = Service(ChromeDriverManager().install())
        return webdriver.Chrome(service=service, options=options)

    def get_driver(self) -> webdriver.Chrome:
        with self.lock:
            return self.driver_pool.pop() if self.driver_pool else self.init_driver()

    def return_driver(self, driver: webdriver.Chrome):
        with self.lock:
            self.driver_pool.append(driver)

    def file_exists_in_db(self, file_hash: str) -> bool:
        return self.pg_manager.check_pdf_record(file_hash)

    def file_exists_in_minio(self, filename: str) -> bool:
        try:
            self.minio_client.stat_object(Config.MINIO_BUCKET, filename)
            return True
        except S3Error:
            return False

   # ------------ Get all company links ------------
    def get_all_company_links(self) -> List[str]:
        driver = self.get_driver()
        company_urls = []
        try:
            driver.get(Config.COMPANY_LIST_URL)
            WebDriverWait(driver, Config.BROWSER_TIMEOUT).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'a[href^="/Company/"]'))
            )
            time.sleep(2)
            elems = driver.find_elements(By.CSS_SELECTOR, 'a[href^="/Company/"]')
            for e in elems:
                href = e.get_attribute("href")
                if href:
                    company_urls.append(href)
        except Exception as e:
            logger.error(f"Failed to obtain company list: {str(e)}")
        finally:
            self.return_driver(driver)
        company_urls = list(set(company_urls))
        logger.info(f"A total of {len(company_urls)} company links were crawled")
        return company_urls

    # ------------ Extract all candidate PDF links ------------
    def get_all_pdf_links(self, company_url: str) -> List[Dict[str, Any]]:
        driver = self.get_driver()
        pdf_info_list = []
        try:
            driver.get(company_url)
            WebDriverWait(driver, Config.BROWSER_TIMEOUT).until(
                EC.presence_of_all_elements_located((By.TAG_NAME, 'a'))
            )
            time.sleep(2)
            links = driver.find_elements(By.TAG_NAME, "a")
            for link in links:
                href = link.get_attribute("href")
                text = link.text or ""
                lower_text = text.lower()
                if href and (re.search(r"20\d{2}", lower_text) or re.search(r"20\d{2}", href)):
                    m = re.search(r"(20\d{2})", lower_text) or re.search(r"(20\d{2})", href)
                    year = int(m.group(1)) if m else datetime.datetime.now().year
                    if not href.startswith("http"):
                        href = "https://www.responsibilityreports.com" + href
                    pdf_info_list.append({
                        "pdf_url": href,
                        "year": year,
                        "link_text": text
                    })
        except Exception as e:
            logger.error(f"Extract all candidate PDF links: {company_url} - {str(e)}")
        finally:
            self.return_driver(driver)
        logger.info(f"[Company Details] {company_url} - Found {len(pdf_info_list)} candidate PDF links")
        return pdf_info_list

    # ------------ Download and store the PDF file ------------
    def download_pdf(self, pdf_url: str, company_name: str, year: int) -> bool:
        safe_company = re.sub(r"[^a-zA-Z0-9_-]+", "_", company_name)
        filename = f"{safe_company}_{year}.pdf"

        for attempt in range(Config.MAX_RETRIES + 1):
            try:
                time.sleep(random.uniform(*Config.RETRY_DELAY))
                response = requests.get(
                    pdf_url,
                    headers={"User-Agent": self.current_user_agent},
                    timeout=Config.REQUEST_TIMEOUT,
                    verify=False,
                    stream=True
                )
                if response.status_code == 200:
                    content = response.content
                    file_hash = hashlib.md5(content).hexdigest()

                    # Deduplication: Database and MinIO
                    if self.file_exists_in_db(file_hash):
                        logger.info(f"Skip stored files (database): {filename}")
                        return False
                    if self.file_exists_in_minio(filename):
                        logger.info(f"Skip stored files (MinIO): {filename}")
                        return False

                    with self.lock:
                        if file_hash in self.seen_hashes:
                            logger.info(f"Duplicate PDF skipped: {pdf_url}")
                            return False
                        self.seen_hashes.add(file_hash)

                    # Upload to MinIO
                    self.minio_client.put_object(
                        Config.MINIO_BUCKET,
                        filename,
                        data=BytesIO(content),
                        length=len(content),
                        content_type="application/pdf"
                    )
                    logger.info(f"Upload MinIO successfully: {filename}")

                    # Inserting into Postgres
                    record = {
                        "company": company_name,
                        "year": year,
                        "url": pdf_url,
                        "filename": filename,
                        "file_hash": file_hash,
                        "created_at": datetime.datetime.now().isoformat()
                    }
                    self.pg_manager.insert_pdf_record(record)
                    logger.info(f"Insert database successfully: {filename}")
                    return True
                else:
                    logger.warning(f"Download status code = {response.status_code}, retrying...")
                    time.sleep(2 ** attempt)
            except S3Error as e:
                logger.error(f"MinIO Upload failed: {e}")
                return False
            except Exception as e:
                logger.warning(f"Download or save failed ({attempt+1}th time): {e}")
                time.sleep(2 ** attempt)
        return False

    # ------------ Validate PDF files (when used for local retention) ------------
    def validate_pdf(self, filepath: str) -> bool:
        try:
            with pdfplumber.open(filepath) as pdf:
                text = "\n".join(page.extract_text() or "" for page in pdf.pages)
                return len(text) >= Config.PDF_MIN_LENGTH and \
                       any(kw in text.lower() for kw in Config.VALID_KEYWORDS)
        except Exception as e:
            logger.error(f"PDF verification exception: {filepath} - {str(e)}")
        return False

    # ------------ Dealing with a single company ------------
    def process_company(self, company_url: str) -> Dict[str, Any]:
        result = {"company_url": company_url, "downloaded": [], "failed": []}
        pdf_candidates = self.get_all_pdf_links(company_url)
        if not pdf_candidates:
            logger.info(f"[{company_url}] No candidate PDF link found")
            return result
        company_name = company_url.rstrip('/').split('/')[-1]
        for info in pdf_candidates:
            pdf_url = info["pdf_url"]
            year = info["year"]
            if pdf_url in self.seen_urls:
                continue
            self.seen_urls.add(pdf_url)
            if self.download_pdf(pdf_url, company_name, year):
                result["downloaded"].append(pdf_url)
            else:
                result["failed"].append(pdf_url)
        return result

    # ------------ Main Process ------------
    def run(self):
        logger.info("Start crawling the full data of responsibilityreports.com...")
        all_company_links = self.get_all_company_links()
        logger.info(f"A total of {len(all_company_links)} company links have been collected. Start downloading the report...")
        with ThreadPoolExecutor(max_workers=Config.MAX_WORKERS) as executor:
            futures = {executor.submit(self.process_company, url): url for url in all_company_links}
            for future in as_completed(futures):
                url = futures[future]
                try:
                    res = future.result()
                    logger.info(f"[DONE] {url} Successfully downloaded {len(res['downloaded'])} PDFs")
                except Exception as e:
                    logger.error(f"[ERROR] {url} abnormal: {str(e)}")
        self.cleanup_drivers()
        logger.info("All crawling completed!")

    # ------------ Clean up the browser instance ------------
    def cleanup_drivers(self):
        with self.lock:
            while self.driver_pool:
                drv = self.driver_pool.pop()
                try:
                    drv.quit()
                except Exception as e:
                    logger.error(f"driver.quit() error: {str(e)}")
# ---------------------------------------------
#                 Program entry
# ---------------------------------------------
if __name__ == "__main__":
    scraper = ResponsibilityReportsScraper()
    scraper.run()
