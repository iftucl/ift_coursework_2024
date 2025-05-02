# Team Magnolia - Coursework One: CSR Report Pipeline Explained (Detailed)

## 1. Introduction

This document provides an in-depth explanation of the Team Magnolia Coursework One project. The primary goal, as outlined in the `coursework_one_instructions`, is to design and implement a system to automatically find, collect, store, and provide access to Corporate Social Responsibility (CSR) reports for a list of companies.

The system leverages several technologies orchestrated via Docker:

*   **Data Sources:** Company list from PostgreSQL. Web search (Bing) for report URLs.
*   **Scraping:** Python with Selenium for browser automation and `requests` for downloading.
*   **Storage:**
    *   MinIO (S3-compatible object storage) for storing the raw PDF report files.
    *   MongoDB for storing metadata about the collected reports (company, year, source URL, storage path, etc.).
*   **API:** FastAPI provides a RESTful interface to query report metadata.
*   **Dashboard:** Streamlit provides a web-based UI for searching, visualizing, and uploading reports.
*   **Orchestration:** Docker Compose manages all the services (databases, storage, scraper, API).
*   **Workflow Management:** A central `main.py` script acts as a command-line interface (CLI) to run different parts of the pipeline.

## 2. Docker Setup (`docker-compose.yml`)

Docker Compose (`docker-compose.yml` in the project root) defines and manages the multi-container application environment.

*   **`mongo_db`**: Standard MongoDB image (`mongo:latest`). Used for storing report metadata. Application connects via `mongodb://mongo_db:27017` within Docker or `mongodb://localhost:27019` locally.
*   **`postgres_db`**: PostgreSQL 10.5 image (`postgres:10.5`). Stores the initial company list in the `fift` database, table `csr_reporting.company_static`. Application connects via host `postgres_db`, port `5432` within Docker or `localhost:5439` locally. Data persisted in `./postgres-data`.
*   **`postgres_seed`**: Builds from `000.Database/SQL/Dockerfile`.
    *   **Purpose:** Initializes the `postgres_db` service. This service is provided as part of the coursework infrastructure and is considered functional. It copies SQL files (`create_db.sql`, `create_tables.sql`) and an `Equity.db` SQLite file into its container.
    *   **Process:** The `CMD` in its Dockerfile runs `psql` to create the `fift` database and the `csr_reporting` schema (as defined in `create_db.sql`), then attempts to create the `csr_reporting.company_static` table (defined in `create_tables.sql`). Subsequently, it uses `sqlite3` to export data from `Equity.db` to a temporary CSV file, and finally uses `psql`'s `\copy` command to import this CSV data into the `csr_reporting.company_static` table.
    *   **Dependencies:** Waits for `postgres_db` to be healthy.
    *   **Note on Observed Discrepancies:** While considered functional, code analysis identified potential discrepancies: the `create_tables.sql` script flagged syntax issues by the linter, and some environment variables/connection strings within the seeding service appeared inconsistent with the target `postgres_db` service name/port. However, for the purpose of this coursework, this seeding mechanism provides the necessary `company_static` table for the scraper.
*   **`pgadmin`**: Standard pgAdmin4 image (`dpage/pgadmin4`). GUI for `postgres_db`. Access via `http://localhost:5051`. Connect to server: host=`postgres_db`, port=`5432`, user=`postgres`, pass=`postgres`.
*   **`miniocw`**: Standard MinIO image (`minio/minio`). S3-compatible storage for PDF reports. Credentials: `ift_bigdata`/`minio_password`. API port `9000`, Console port `9001` (`http://localhost:9001`).
*   **`minio_client_cw`**: MinIO Client image (`minio/mc`). Helper to auto-configure MinIO. Waits for `miniocw`, adds host config, removes/creates `csreport` bucket, sets public access. Ensures bucket is ready.
*   **`selenium`**: Selenium standalone Chrome image (`selenium/standalone-chromium:latest`). Provides a remote browser for the scraper. WebDriver connects to `http://selenium:4444/wd/hub`. VNC access at `http://localhost:7900`.
*   **`magnolia_scraper`**: **The application container.**
    *   **Build:** Uses `Team_Magnolia/coursework_one/Dockerfile`.
    *   **Connectivity:** Connects to `default` network (for mongo, postgres, selenium) and `iceberg_net` (for minio).
    *   **Environment Variables (Crucial for Code):**
        *   `DOCKER_ENV=true`: Signals Python code to use Docker service names (e.g., `mongo_db`) instead of `localhost`.
        *   `MONGO_URI=mongodb://mongo_db:27017`: Used by Pymongo.
        *   `MINIO_HOST=miniocw:9000`: Used by Minio client.
        *   `POSTGRES_HOST=postgres_db`: Used by Psycopg2.
        *   `SELENIUM_URL=http://selenium:4444/wd/hub`: Used by Selenium WebDriver.
    *   **Port Mapping:** Host `8000` to Container `8000` for FastAPI access.

## 3. Core Workflow Orchestrator (`main.py`)

Acts as the main entry point and CLI dispatcher using `argparse`.

*   **Imports:** Attempts to import `main` functions from core modules (`csr_scraper`, `analysis_pipeline`, `csr_fix_and_cleanup`, `mongo_index_setup`) and the `app` from `fastapi_api`. Uses `try/except ImportError` to handle missing modules gracefully (though all seem present). Imports `uvicorn` for running FastAPI.
*   **Logging:** Basic logging configured to show timestamp, level, logger name, and message.
*   **`parse_args()`:** Defines the command-line interface structure:
    *   `parser = argparse.ArgumentParser(...)`
    *   `subparsers = parser.add_subparsers(dest="command", required=True)`: Creates subcommands.
    *   **`scrape` subcommand:** Takes optional `--max-companies` (int).
    *   **`analysis` subcommand (Commented Out):** Would take `--quick` flag.
    *   **`fix` subcommand:** Takes optional `--dry-run` flag.
    *   **`index` subcommand:** No arguments.
    *   **`api` subcommand:** Takes `--host` (str, default `0.0.0.0`), `--port` (int, default `8000`), `--reload` (flag).
*   **`main()`:**
    1.  Calls `parse_args()` to get user command and options.
    2.  Uses `if/elif` chain on `args.command`:
        *   **`scrape`**: Logs start/end, calls `run_scraper(max_companies=args.max_companies)` if imported.
        *   **`analysis`**: Logs start/end, calls `run_analysis(quick_mode=args.quick)` if imported (currently commented out).
        *   **`fix`**: Logs start/end, calls `run_fix_and_cleanup(dry_run=args.dry_run)` if imported.
        *   **`index`**: Logs start/end, calls `setup_indexes()` if imported.
        *   **`api`**: Logs start/end, calls `uvicorn.run("modules.api.fastapi_api:app", host=args.host, port=args.port, reload=args.reload)` if `fastapi_app` imported.
    3.  Handles cases where modules might fail to import by logging an error.

**Execution:** You run commands like `python main.py scrape`, `python main.py fix --dry-run`, `python main.py api --reload`.

## 4. Scraping Module (`modules/scraper/csr_scraper.py`)

This module performs the automated discovery and collection of CSR reports.

*   **Imports:** `os`, `sys`, `time`, `datetime`, `urllib.parse`, `concurrent.futures`, `requests`, `apscheduler`, `selenium` (webdriver, options, By, WebDriverWait, EC), `chromedriver_autoinstaller`, `psycopg2`, `pymongo`, `minio`.
*   **Configuration (`DB_CONFIG`, `MONGO_URI`, `MINIO_HOST`, `PROXY`):**
    *   Uses `os.environ.get("DOCKER_ENV") == "true"` to conditionally set database/service hostnames (`postgres_db`, `mongo_db`, `miniocw`) for Docker or `localhost` (with specific ports `5439`, `27019`, `9000`) for local execution. Reads corresponding environment variables if set, otherwise falls back to defaults.
    *   Initializes global `mongo_client` (Pymongo), `mongo_db`, `collection_reports`, and `MINIO_CLIENT` (Minio).
*   **Logging (`LOG_FILE`, `write_log`)**: Logs messages with timestamps to console and a file (`csr_fast.log` or `test_log.log` if running in pytest).
*   **`init_driver()`**:
    *   Configures `selenium.webdriver.chrome.options.Options` (disables GPU, sandbox, sets log level). `headless=new` is commented out, so it runs with a visible browser window locally if not using Selenium Grid.
    *   Checks `os.environ.get("SELENIUM_URL")`.
        *   If set (in Docker): Initializes `webdriver.Remote` pointing to the Selenium Grid URL.
        *   If not set (local): Calls `chromedriver_autoinstaller.install()` to ensure the correct driver is present, then initializes `webdriver.Chrome`.
    *   Returns the Selenium `driver` instance.
*   **`get_search_results(driver, query, timeout=5)`**:
    *   Constructs a Bing search URL: `https://www.bing.com/search?q=<url_encoded_query>`.
    *   Navigates the `driver` to the URL.
    *   Uses `WebDriverWait(driver, timeout)` to wait until search result links (`By.CSS_SELECTOR, ".b_algo h2 a"`) are present.
    *   Finds all matching elements (`driver.find_elements`).
    *   Logs success/failure and number of results.
    *   Returns the list of Selenium WebElement objects representing the links. Handles potential exceptions during waiting/finding.
*   **`download_pdf(company_name, year, url)`**:
    *   Logs download start.
    *   **Basic Validation:** Checks if `"pdf"` (case-insensitive) is in the `url`. If not, logs a warning and returns `None`.
    *   Creates `./reports` directory if needed.
    *   Constructs local path: `./reports/<company_name>_<year>.pdf`.
    *   Uses `requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=5)` to fetch the PDF.
    *   If `resp.status_code == 200`: Writes `resp.content` (binary PDF data) to the local path. Logs success and returns `local_path`.
    *   If status code is not 200 or other exception occurs: Logs failure and returns `None`.
*   **`upload_to_minio(company_name, year, local_path)`**:
    *   Constructs the `object_name` (MinIO path): `<year>/<company_name>.pdf`.
    *   Logs upload start.
    *   Uses the global `MINIO_CLIENT`'s `put_object` method:
        *   `bucket_name=BUCKET_NAME` (`csreport`)
        *   `object_name=object_name`
        *   `data=f` (file handle opened in binary read mode `rb`)
        *   `length=os.path.getsize(local_path)` (required for stream uploads)
        *   `content_type="application/pdf"`
    *   Logs success and returns `object_name`.
    *   If exception occurs: Logs failure and returns `None`.
*   **`save_csr_report_info_to_mongo(company_name, pdf_url, object_name, year)`**:
    *   Creates a dictionary `data` containing: `company_name`, original `pdf_url`, MinIO `storage_path` (`object_name`), `csr_report_year` (int), and `ingestion_time` (`datetime.datetime.utcnow()`).
    *   Uses the global `collection_reports` (Pymongo collection object) `update_one` method:
        *   **Filter:** `{"company_name": company_name, "csr_report_year": year}` - Matches based on company and year.
        *   **Update:** `{"$set": data}` - Sets/updates fields with the new `data`.
        *   **`upsert=True`**: If no document matches the filter, inserts the `data` as a new document. If a match exists, updates it. This makes the process idempotent.
    *   Logs success/failure.
*   **`get_company_list_from_postgres()`**:
    *   Logs connection attempt.
    *   Uses `psycopg2.connect(**DB_CONFIG)` to connect to PostgreSQL (details depend on `DOCKER_ENV`).
    *   Executes `SELECT security FROM csr_reporting.company_static;`. **Relies on the `postgres_seed` service having successfully created and populated this table.**
    *   Fetches all rows (`cur.fetchall()`).
    *   Extracts the first column (`row[0]`, assumed to be the company name) from each row into a list.
    *   Closes cursor and connection.
    *   Logs success and number of companies found. Returns the list of names.
    *   If exception occurs: Logs failure and returns an empty list `[]`.
*   **`search_by_years(driver, company_name, years, keywords)`**:
    *   Iterates through the specified `years` (e.g., `range(2020, 2025)`).
    *   **Resume Check:** For each `year`, checks MongoDB `collection_reports.find_one({"company_name": company_name, "csr_report_year": year})`. If a record exists, logs a skip message and `continue`s to the next year.
    *   Iterates through `keywords` (e.g., `"corporate sustainability report filetype:pdf"`).
    *   Constructs the search `query` (e.g., `"Apple 2023 corporate sustainability report filetype:pdf"`).
    *   Calls `get_search_results(driver, query)` to get link elements.
    *   **Stale Element Handling:** Iterates through result elements *immediately* and extracts `href` attributes into a separate `links` list, catching potential `StaleElementReferenceException` if the page changes during iteration.
    *   Iterates through the extracted `links` (URLs):
        *   Calls `download_pdf(company_name, year, url)`.
        *   If `pdf_path` is returned (download successful):
            *   Calls `upload_to_minio(company_name, year, pdf_path)`.
            *   If `obj_name` is returned (upload successful):
                *   Calls `save_csr_report_info_to_mongo(company_name, url, obj_name, year)`.
            *   Sets `found_any = True`.
            *   Deletes the temporary local file: `os.remove(pdf_path)`.
    *   `time.sleep(0.2)`: Small delay between keyword searches.
    *   Returns `found_any` (boolean indicating if at least one PDF was processed for this company).
*   **`search_and_process(company_name)`**:
    *   This function is designed to be run by the `ThreadPoolExecutor`.
    *   Logs start for the company.
    *   Calls `init_driver()` to get a dedicated Selenium driver instance for this thread/company.
    *   Defines `years = range(2020, 2025)` and `keywords`.
    *   Calls `search_by_years(driver, company_name, years, keywords)`.
    *   Logs if no PDF was found for the company.
    *   Includes a `finally` block to ensure `driver.quit()` is always called, closing the browser instance even if errors occur. Handles potential exceptions during processing.
*   **`process_batch(company_list)`**:
    *   Reads `CSR_MAX_WORKERS` environment variable (defaults to 3). Logs the number of workers.
    *   Creates a `concurrent.futures.ThreadPoolExecutor(max_workers=...)`.
    *   Uses `executor.map(search_and_process, company_list)`. This applies the `search_and_process` function to each `company_name` in the `company_list`, distributing the work across the thread pool.
*   **`schedule_scraper()`**:
    *   Uses `apscheduler.schedulers.blocking.BlockingScheduler`.
    *   Adds a job to run the `main` function (the entire scraping process) at a fixed interval (`days=7`).
    *   Starts the scheduler (`scheduler.start()`), which blocks execution. Designed to be run in the background (e.g., via `docker exec -d ...`) for periodic scraping. Handles `KeyboardInterrupt`. **Not called by default.**
*   **`main(max_companies=None)`**:
    *   Calls `get_company_list_from_postgres()` to get target companies.
    *   If `max_companies` argument is provided, slices the list `companies = companies[:max_companies]`.
    *   **Bucket Creation:** Checks if `BUCKET_NAME` (`csreport`) exists in MinIO using `MINIO_CLIENT.bucket_exists()` and creates it using `MINIO_CLIENT.make_bucket()` if it doesn't.
    *   Calls `process_batch(companies)` to start the concurrent scraping.
    *   Logs completion.
*   **`if __name__ == "__main__":`**: Calls `main()` when the script is executed directly (`python modules/scraper/csr_scraper.py`).

## 5. Data Storage Details

The project utilizes three primary storage systems:

*   **PostgreSQL (`postgres_db` service):**
    *   **Database:** `fift` (created by `postgres_seed` via `create_db.sql`)
    *   **Schema:** `csr_reporting` (created by `postgres_seed` via `create_db.sql`)
    *   **Table:** `company_static`
        *   **Purpose:** Stores the *input* list of companies the scraper should target. Populated by the `postgres_seed` service from `Equity.db`.
        *   **Schema (from `create_tables.sql`):**
            *   `"symbol"`: `CHAR(12)` - Primary Key. Likely a stock ticker or unique ID.
            *   `"security"`: `TEXT` - The company name, used by the scraper as the primary identifier for searching.
            *   `"gics_sector"`: `TEXT` - Global Industry Classification Standard sector.
            *   `"gics_industry"`: `TEXT` - Global Industry Classification Standard industry.
            *   `"country"`: `TEXT` - Company's country.
            *   `"region"`: `TEXT` - Company's region.
    *   **Interaction:** Read by `csr_scraper.py` (`get_company_list_from_postgres`) to get the list of `security` names to process.

*   **MinIO (`miniocw` service):**
    *   **Purpose:** Stores the actual CSR report PDF files (the binary data). Acts as the data lake component.
    *   **Bucket:** `csreport` (created automatically by the `minio_client_cw` service). Public read access is set by `minio_client_cw`.
*   **MongoDB (`mongo_db` service):**
    *   **Purpose:** Stores metadata *about* each collected CSR report, enabling efficient search and retrieval without parsing PDFs.
    *   **Document Structure (Example):**
        ```json
        {
          "_id": ObjectId("60f1b7e8a3b4c5d6e7f8a9b0"), // Auto-generated by MongoDB
          "company_name": "Example Corp",
          "csr_report_url": "https://example.com/reports/csr_2023.pdf", // Original URL found by scraper
          "storage_path": "2023/Example Corp.pdf", // Path within the 'csreport' MinIO bucket
          "csr_report_year": 2023, // Target year for search, potentially corrected by 'fix' script
          "ingestion_time": "2024-07-15T14:22:30.123456", // UTC timestamp (ISO format string after 'fix') from scraper run
          // Optional 'analysis' sub-document added by analysis_pipeline.py:
          "analysis": {
            "sentiment_score": 0.65, // Overall sentiment score (-1 to +1) from VADER
            "keywords": ["sustainability", "renewable energy", "community", "governance", "emissions"] // Top 5 keywords from YAKE
          }
        }
        ```
    *   **Indexes:** Created by `mongo_index_setup.py` (run via `python main.py index`):
        *   Compound: `company_name` (ascending), `csr_report_year` (ascending) - Speeds up common API queries.
        *   Single: `csr_report_year` (ascending) - Speeds up year-only filters.
        *   Text: `company_name` - Allows efficient text search on company name (though API uses regex).
    *   **Interaction:** Written to by `csr_scraper.py` (`save_csr_report_info_to_mongo` - upsert), read/updated by `csr_fix_and_cleanup.py`, read/updated by `analysis_pipeline.py`, read by `fastapi_api.py`, read/written to by `streamlit_app.py` (manual upload).

## 6. Data Cleanup Module (`modules/scraper/csr_fix_and_cleanup.py`)

Refines and corrects data in MongoDB and MinIO after scraping.

*   **Imports:** `os`, `re`, `datetime`, `pdfplumber`, `magic`, `pymongo`, `minio`.
*   **Configuration:** Similar conditional logic using `DOCKER_ENV` for `MONGO_URI` and `MINIO_HOST`. Initializes global `MINIO_CLIENT` and MongoDB connection (`mongo_client`, `mongo_db`, `collection_reports`).
*   **Logging:** Similar `write_log` function, writing to `csr_fix_and_cleanup.log`.
*   **`is_valid_pdf(file_path)`**: Uses `magic.Magic(mime=True).from_file(file_path)` to get the MIME type from file *content* and returns `True` if it's `"application/pdf"`.
*   **`delete_invalid_pdf_from_minio(object_name)`**: Uses `MINIO_CLIENT.remove_object(BUCKET_NAME, object_name)` to delete a file from MinIO. Logs success/failure.
*   **`download_pdf_from_minio(object_name, local_path)`**:
    *   Uses `MINIO_CLIENT.fget_object(BUCKET_NAME, object_name, local_path)` to download the file.
    *   Calls `is_valid_pdf(local_path)` to check the downloaded file.
    *   If invalid: Logs warning, deletes the local file (`os.remove`), calls `delete_invalid_pdf_from_minio` to remove it from storage, and returns `False`.
    *   Returns `True` if download and validation succeed. Handles exceptions.
*   **`extract_year_from_pdf(file_path)`**:
    *   Uses `pdfplumber.open(file_path)` to open the PDF.
    *   Iterates through the first two pages (`pdf.pages[:2]`).
    *   Extracts text using `page.extract_text() or ""`.
    *   Uses `re.search(r"20\d{2}", text)` to find the first 4-digit number starting with "20".
    *   If found, returns `int(match.group(0))`.
    *   If not found after checking two pages, or if an error occurs, returns `None`. Handles exceptions.
*   **`update_csr_year()`**:
    *   Gets all documents from `collection_reports.find()`.
    *   Creates local temp directory `./reports`.
    *   Iterates through documents:
        *   Gets `company_name`, `object_name` (`storage_path`).
        *   Constructs `local_path` (replacing '/' in object_name for safe filename).
        *   Calls `download_pdf_from_minio`. If it returns `False`, `continue`s to the next document.
        *   Calls `extract_year_from_pdf(local_path)`.
        *   If `actual_year` is found: Updates the MongoDB document using `collection_reports.update_one({"_id": doc["_id"]}, {"$set": {"csr_report_year": actual_year}})`. Logs success.
        *   If no year found: Logs failure.
        *   Deletes the temporary local file `os.remove(local_path)`.
*   **`fix_ingestion_time()`**:
    *   Gets all documents from `collection_reports.find()`.
    *   Iterates through documents:
        *   Checks if `doc.get("ingestion_time")` is an instance of `datetime.datetime`.
        *   If yes: Updates the MongoDB document, setting `ingestion_time` to `ingestion_time.isoformat()`. Logs success.
*   **`delete_duplicate_pdfs()`**:
    *   Fetches *all* documents into a list: `all_docs = list(collection_reports.find())`. **Inefficient for very large collections.**
    *   Initializes `seen = {}` dictionary to track unique `(company, year)` pairs.
    *   Iterates through `all_docs`:
        *   Extracts `comp`, `year`, `obj_path`, `doc_id`. Skips if `year` is missing.
        *   Creates `key = (comp, year)`.
        *   If `key not in seen`: Stores the first occurrence: `seen[key] = doc_id`.
        *   If `key in seen`: This is a duplicate. Logs finding.
            *   Calls `MINIO_CLIENT.remove_object(BUCKET_NAME, obj_path)` to delete the PDF from storage. Handles potential errors.
            *   Calls `collection_reports.delete_one({"_id": doc_id})` to delete the metadata record from MongoDB.
*   **`main(dry_run=False)`**:
    *   Logs start message. Checks `dry_run` flag.
    *   If not `dry_run`: Calls `update_csr_year()`, `fix_ingestion_time()`, `delete_duplicate_pdfs()` in sequence, logging progress.
    *   Logs completion.
*   **`if __name__ == "__main__":`**: Calls `main()` when script is executed directly.

## 7. Analysis Pipeline (`modules/api/analysis_pipeline.py`)

Performs NLP tasks (sentiment, keywords) on PDFs. **Standalone script.**

*   **Imports:** `os`, `io`, `pymongo`, `minio`, `pdfplumber`, `nltk` (specifically `SentimentIntensityAnalyzer`), `yake`.
*   **Configuration:** Hardcoded `MONGO_URI = "mongodb://localhost:27019"` and MinIO details (`localhost:9000`, credentials). **Does not use `DOCKER_ENV`.** Needs manual adjustment if run in Docker. Initializes MongoDB and MinIO clients.
*   **`nltk.download('vader_lexicon')`**: Commented out, but **required** to be run once beforehand for `SentimentIntensityAnalyzer` to work.
*   **`extract_text_from_pdf(pdf_bytes)`**: Takes PDF content as `bytes`. Opens it using `pdfplumber.open(io.BytesIO(pdf_bytes))`. Iterates through all pages, extracts text (`page.extract_text() or ""`), concatenates, and returns the full text string.
*   **`sentiment_analysis(text)`**: Initializes `nltk.sentiment.SentimentIntensityAnalyzer()`. Calls `sia.polarity_scores(text)`. Returns the `compound` score (float between -1 and 1).
*   **`keyword_extraction(text, max_k=5)`**: Initializes `yake.KeywordExtractor(n=1, top=max_k)` (extracts single words, top 5 by default). Calls `kw_extractor.extract_keywords(text)`. Returns a list of the keyword strings `[k[0] for k in keywords]`.
*   **`run_analysis()`**:
    *   Fetches all documents: `docs = list(collection.find())`.
    *   Iterates through `docs`:
        *   Gets `storage_path`. Skips if missing.
        *   Downloads PDF from MinIO into `pdf_bytes` using `MINIO_CLIENT.get_object(BUCKET_NAME, path).read()`. Handles exceptions during download.
        *   Calls `extract_text_from_pdf(pdf_bytes)`. Skips if no text extracted.
        *   Calls `sentiment_analysis(text)` to get `sentiment_score`.
        *   Calls `keyword_extraction(text, max_k=5)` to get `keywords`.
        *   Updates the MongoDB document using `collection.update_one({"_id": doc["_id"]}, {"$set": {"analysis.sentiment_score": sentiment_score, "analysis.keywords": keywords}})` creating/updating an embedded `analysis` object. Logs results.
*   **`if __name__ == "__main__":`**: Calls `run_analysis()`.

## 8. API Module (`modules/api/fastapi_api.py`)

Provides a REST API to access report metadata using FastAPI.

*   **Imports:** `fastapi` (FastAPI, HTTPException, Query), `fastapi.responses` (FileResponse), `pymongo`, `pydantic` (BaseModel), `typing` (List, Optional), `datetime`, `os`, `logging`, `shutil`.
*   **Logging:** Basic logging setup.
*   **Configuration:** Hardcoded `MONGO_URI = "mongodb://localhost:27019"`, `MONGO_DB_NAME`, `MONGO_COLLECTION`. **Does not use `DOCKER_ENV`.** Needs manual adjustment if run in Docker. Initializes MongoDB client. `MINIO_HOST` read from env var or defaults to `localhost`. `MINIO_BUCKET` hardcoded (`csreport`).
*   **FastAPI App:** `app = FastAPI(...)` initializes the application with title, description, version. Provides interactive API docs (e.g., at `/docs` by default).
*   **Pydantic Models:** Define data shapes for request/response validation and API documentation.
    *   `CSRReport(BaseModel)`:
        *   `company_name: str`
        *   `csr_report_url: str`
        *   `storage_path: str`
        *   `csr_report_year: int`
        *   `ingestion_time: str`
        *   `download_link: Optional[str] = None` (Dynamically generated in the endpoint)
    *   `BatchDownloadRequest(BaseModel)`:
        *   `report_paths: List[str]` (Expects a JSON array of strings in the request body)
*   **`GET /reports` Endpoint (`get_reports` function):**
    *   **Purpose:** Retrieve a list of CSR reports, optionally filtered by company and/or year.
    *   **Parameters:** Defined using `fastapi.Query`:
        *   `company: Optional[str] = Query(None, description="...")`: Optional company name filter.
        *   `year: Optional[int] = Query(None, description="...")`: Optional report year filter.
    *   **Logic:**
        1.  Builds a `query` dictionary for MongoDB's `find()` method.
        2.  If `company` provided, adds `{"company_name": {"$regex": company, "$options": "i"}}`. The `$regex` allows partial matching, and `$options: "i"` makes it case-insensitive.
        3.  If `year` provided, adds `{"csr_report_year": year}` for an exact match.
        4.  Executes `collection_reports.find(query, {"_id": 0})`. The projection `{ "_id": 0 }` excludes the internal MongoDB object ID.
        5.  Converts the cursor result to a list `reports`.
        6.  If `reports` is empty, raises `HTTPException(status_code=404, detail="No reports found...")`.
        7.  Iterates through the `reports` list:
            *   Ensures `ingestion_time` is a string (converts if it's a `datetime` object).
            *   Constructs the `download_link` string: `f"http://{MINIO_HOST}:9000/{MINIO_BUCKET}/{report['storage_path']}"`. This provides a direct URL to the PDF in MinIO (requires MinIO bucket to be public or appropriate access).
            *   Adds the processed `report` dictionary to the `results` list.
    *   **Response:** Returns the `results` list. FastAPI automatically serializes this to JSON. The `response_model=List[CSRReport]` decorator ensures the output conforms to the specified Pydantic model and adds this information to the API documentation.
    *   **Error Handling:** Includes a `try...except HTTPException...except Exception` block to catch specific 404s and general server errors (returning 500).
*   **`POST /download-zip` Endpoint (`download_reports` async function):**
    *   **Purpose:** Download multiple specified reports as a single ZIP archive.
    *   **Request Body:** Expects a JSON object matching `BatchDownloadRequest`, e.g., `{"report_paths": ["2023/CompanyA.pdf", "2022/CompanyB.pdf"]}`. FastAPI automatically parses the JSON into the `request` object.
    *   **Logic:**
        1.  Checks if `request.report_paths` list is empty. If so, raises `HTTPException(status_code=400, detail="No reports selected...")`.
        2.  Sets up temporary directory (`./temp_reports`) and output zip path (`./csr_reports.zip`). Cleans up any previous versions.
        3.  Iterates through each `report_path` in the input list.
        4.  **MOCK DOWNLOAD:** Creates a local file path. **Crucially, it writes dummy text content `with open(local_path, "w") as f: f.write("Dummy PDF content")`. It does NOT actually download the file from MinIO.**
        5.  After the loop, uses `shutil.make_archive` to create a ZIP file from the contents of the temporary directory (containing the dummy files).
    *   **Response:** Returns a `fastapi.responses.FileResponse`. This streams the contents of the generated ZIP file back to the client with the appropriate headers (`media_type="application/zip"`, `filename="csr_reports.zip"`).
    *   **Improvement Needed:** The mock download step must be replaced with actual calls to a MinIO client (e.g., `MINIO_CLIENT.fget_object(MINIO_BUCKET, report_path, local_path)`) to make this endpoint functional.
    *   **Error Handling:** Catches the 400 error and any other exceptions (returning 500).
*   **Execution (`if __name__ == "__main__":`)**: Allows running the API directly using `uvicorn` for local development, typically enabling reload. In the deployed setup, it's intended to be run via `python main.py api`.

## 9. Indexing Utility (`modules/api/mongo_index_setup.py`)

Ensures efficient MongoDB querying.

*   **Imports:** `pymongo`, `os`.
*   **Configuration:** Reads `MONGO_URI` from environment or defaults to `mongodb://localhost:27019`. **Does not use `DOCKER_ENV`.** Initializes MongoDB client.
*   **`setup_indexes()`**:
    *   Calls `collection_reports.create_index` multiple times:
        *   Compound index on `[("company_name", 1), ("csr_report_year", 1)]`.
        *   Single index on `[("csr_report_year", 1)]`.
        *   Text index on `[("company_name", "text")]`.
    *   Prints success message and current index information (`collection_reports.index_information()`).
*   **`if __name__ == "__main__":`**: Calls `setup_indexes()`. Run via `python main.py index`.

## 10. Dashboard App (`modules/api/streamlit_app.py`)

Provides a web UI for interacting with the data using Streamlit.

*   **Imports:** `streamlit`, `requests`, `pandas`, `altair`, `io`, `zipfile`, `os`, `datetime`, `minio`, `pymongo`.
*   **Configuration:**
    *   `API_BASE_URL = "http://localhost:8000"`: Hardcoded URL for the FastAPI backend. **Requires FastAPI to be running and accessible from where Streamlit runs.**
    *   **Direct DB/MinIO Access:** Initializes its *own* Pymongo (`MongoClient("mongodb://localhost:27019")`) and Minio (`Minio("localhost:9000", ...)` clients. **These hardcoded `localhost` values mean the Streamlit app needs direct network access to the host machine's ports 27019 and 9000, even if run inside a container, unless specific Docker network modes (like `host`) are used.** This direct access is necessary for the Manual Upload and Batch Download features as implemented.
*   **UI Layout:** Standard Streamlit (`st.set_page_config`, `st.title`, sidebar elements).
*   **Search (`search_reports`, Search Button):** Uses `requests` to call the `GET /reports` endpoint of the FastAPI backend based on sidebar inputs. Displays results in `st.dataframe`. Stores results in `st.session_state`.
*   **Batch Download (Button Logic):**
    *   Allows user selection via `st.multiselect`.
    *   On button click, iterates selected rows.
    *   Gets `download_link` (direct MinIO URL) for each selected report from the DataFrame (which originally came from the API).
    *   Uses `requests.get()` to download the PDF content **directly from the MinIO URL**.
    *   Uses `zipfile` to create an in-memory ZIP (`io.BytesIO`).
    *   Uses `st.download_button` to offer the generated ZIP to the user. **This successfully bypasses the non-functional `POST /download-zip` API endpoint.**
*   **Visualization:** Fetches all data via `GET /reports`, processes with Pandas, displays an Altair bar chart of reports per year.
*   **Manual Upload (Section Logic):**
    *   Uses `st` input widgets.
    *   On button click:
        *   Constructs MinIO `storage_path`.
        *   Uses the Streamlit app's **direct MinIO client** (`minio_client.put_object`) to upload the file from the `st.file_uploader`.
        *   Uses the Streamlit app's **direct MongoDB client** (`collection_reports.insert_one`) to insert the metadata.
        *   Provides success/error feedback using `st.success`/`st.error`. **This completely bypasses the scraper and API.**
*   **Execution:** Run via `streamlit run modules/api/streamlit_app.py`. Requires the FastAPI service to be running at `API_BASE_URL`. For full functionality (batch download, manual upload), requires direct network access to the MinIO and MongoDB ports defined *within this script*.

## 11. Unused/Problematic Components Revisited

*   **`modules/db/db_connection.py` & `modules/minio_ops/minio_client.py`:** Confirmed unused. The core modules (`csr_scraper`, `csr_fix_and_cleanup`) initialize their own clients based on environment variables (`DOCKER_ENV`). The API and Streamlit app also initialize their own clients, but using hardcoded `localhost` URIs/hosts. These modules rely on a `config/conf.yaml` file which is also marked as unused and likely doesn't contain the expected keys (`config["minio"]`, `config["database"]["postgresql"]`). **Safe to ignore or remove.**
*   **`config/conf.yaml`:** Confirmed unused and likely deprecated. Configuration is via `docker-compose.yml` environment variables and hardcoded values in API/Streamlit. **Safe to ignore or remove.**
*   **SQL Errors (`000.Database/SQL/create_tables.sql`) & Seeding Issues:** While the seeding process is considered functional as provided infrastructure for the coursework, the observed linter errors in the SQL script and potential configuration mismatches in the Docker setup are noted. For the project's execution, we assume the `postgres_seed` service successfully creates and populates the `csr_reporting.company_static` table in the `fift` database on the `postgres_db` service.

## 12. Data Flow Summary

1.  **Initialization (Requires Fix):** `postgres_seed` service (attempts to) create `csr_reporting.company_static` table in `postgres_db` and populate it with company names. `minio_client_cw` creates the `csreport` bucket in `miniocw`.
2.  **Scraping (`main.py scrape` -> `csr_scraper.py`):**
    *   Reads company list from `postgres_db`.`csr_reporting`.`company_static`.
    *   For each company/year: Checks `mongo_db`.`csr_reports` if data exists.
    *   If not exists: Uses `selenium` service to search Bing for PDF URLs.
    *   Downloads PDF via `requests`.
    *   Uploads PDF to `miniocw` (e.g., `csreport/2023/Company.pdf`).
    *   Upserts metadata (company, year, original URL, MinIO path, timestamp) into `mongo_db`.`csr_reports`.
3.  **Cleanup (`main.py fix` -> `csr_fix_and_cleanup.py`):**
    *   Reads metadata from `mongo_db`.`csr_reports`.
    *   Downloads corresponding PDF from `miniocw`.
    *   Validates PDF type using `magic`. Deletes invalid PDFs from `miniocw`.
    *   Extracts year from PDF content using `pdfplumber`. Updates `csr_report_year` in `mongo_db`.
    *   Standardizes `ingestion_time` format in `mongo_db`.
    *   Identifies duplicate (company, year) entries in `mongo_db`. Deletes duplicate metadata from `mongo_db` and corresponding PDF from `miniocw`.
4.  **Indexing (`main.py index` -> `mongo_index_setup.py`):** Creates indexes directly on `mongo_db`.`csr_reports` collection for faster queries.
5.  **Analysis (Manual Run -> `analysis_pipeline.py`):**
    *   Reads metadata from `mongo_db`.`csr_reports` (via hardcoded `localhost` connection).
    *   Downloads PDF from `miniocw` (via hardcoded `localhost` connection).
    *   Extracts text using `pdfplumber`.
    *   Performs sentiment analysis (`nltk`) and keyword extraction (`yake`).
    *   Updates `mongo_db`.`csr_reports` document with an `analysis` sub-document.
6.  **API Access (`main.py api` -> `fastapi_api.py`):**
    *   Listens on port 8000.
    *   `GET /reports`: Queries `mongo_db`.`csr_reports` based on `company` (regex) and `year`. Returns metadata including a direct download link to `miniocw`.
    *   `POST /download-zip`: **(Currently Mocked)** Intended to receive MinIO paths, download files from `miniocw`, zip them, and return the zip file.
7.  **Dashboard (Manual Run -> `streamlit_app.py`):**
    *   Communicates with FastAPI (`http://localhost:8000/reports`) for searching and visualization data.
    *   **Batch Download:** Gets MinIO links from API, then downloads PDFs directly from `miniocw` using `requests` (via `localhost:9000` connection configured in Streamlit). Zips locally.
    *   **Manual Upload:** Writes PDF file directly to `miniocw` (via `localhost:9000`) and metadata directly to `mongo_db` (via `localhost:27019`) using its own clients.

## 13. Fulfillment of Requirements (`coursework_one_instructions`)

*   **Identify & Ingest:** Yes (Scraper).
*   **Persistent Storage:** Yes (MinIO for PDFs, MongoDB for metadata).
*   **Flexible Design:** Yes (Postgres for company list, year search/filter, idempotent scraper/cleanup). Scheduling mechanism exists but isn't run by default.
*   **Data Lake (MinIO):** Yes.
*   **Technology Stack:** Yes (Docker, Python, MinIO, MongoDB, PostgreSQL). Missing Kafka.
*   **Dockerization:** Yes.
*   **Python Specifications:**
    *   *Poetry:* Yes.
    *   *Flexibility:* Yes (CLI, Env Vars).
    *   *Testing/Linting/Docs/Security:* **Likely incomplete/missing.** No clear evidence of `pytest` tests, `flake8`/`black` integration, Sphinx docs, or security scans in the provided structure.
*   **Submission:** Structure matches.

## 14. Conclusion (Enhanced)

Team Magnolia's Coursework One project implements a multi-stage pipeline for CSR report collection using a relevant tech stack orchestrated by Docker. The core workflow involves scraping data based on a PostgreSQL list (provided by the functional, albeit potentially inconsistently configured, seeding service), storing PDFs in MinIO and metadata in MongoDB, followed by optional cleanup, analysis, and access via API and a Streamlit dashboard. Key strengths include the modular design managed by `main.py`, the use of environment variables for flexible deployment in the scraper/cleanup modules, and the idempotent nature of the scraper and cleanup tasks.

**Key Implementation Details & Areas for Review:**

1.  **Configuration Inconsistency:** The core pipeline (`scraper`, `cleanup`) uses `DOCKER_ENV` to switch between Docker service names and `localhost`. However, the `API` and `Streamlit` modules use hardcoded `localhost` connections, potentially hindering portability and requiring specific network setups (like host mode or relying on host port mappings) when running the full stack in Docker. Standardizing configuration (e.g., using environment variables everywhere) is recommended.
2.  **API Batch Download:** The `POST /download-zip` endpoint currently uses mock file creation instead of downloading from MinIO. The Streamlit dashboard correctly bypasses this by downloading directly. The API endpoint needs fixing if it's intended to be used.
3.  **Standalone Modules:** The `analysis_pipeline.py` is not integrated into the `main.py` CLI and requires manual execution and setup (NLTK download).
4.  **Direct DB/Storage Access in UI:** The Streamlit app's manual upload and batch download features interact directly with MongoDB and MinIO clients configured within the Streamlit script itself (using `localhost`). While functional, this bypasses the API layer for these operations.
5.  **Coursework Requirements:** Ensure that testing (`pytest`), linting (`flake8`), formatting (`black`), documentation (`Sphinx`), and security scanning requirements outlined in the instructions are fully implemented and demonstrable.

## 15. Integration Plan: Upgrading Scraper with Standalone Finder/Downloader Logic

**Goal:** Replace the existing Bing search (`get_search_results`) and basic `requests` download (`download_pdf`) in `csr_scraper.py` with the more robust Google CSE + Groq finding logic from `standalone_report_finder2.py` and the direct/Selenium fallback download logic from `standalone_pdf_downloader.py`. The overall workflow involving Postgres, MinIO, MongoDB, and multithreading will be preserved.

**Steps:**

1.  **Dependency Management:**
    *   Add necessary new dependencies to `pyproject.toml`:
        ```toml
        [tool.poetry.dependencies]
        # ... other dependencies
        google-api-python-client = "^2.0.0" # Or appropriate version
        google-auth-httplib2 = "^0.1.0"
        google-auth-oauthlib = "^0.4.1"
        groq = "^0.5.0" # Or appropriate version
        beautifulsoup4 = "^4.12.0"
        loguru = "^0.7.0"
        webdriver-manager = "^4.0.0"
        # Ensure requests, selenium, pymongo, minio, psycopg2-binary are still present
        ```
    *   Run `poetry lock` to update the `poetry.lock` file.
    *   Run `poetry export -f requirements.txt --output requirements.txt --without-hashes` to update `requirements.txt`.

2.  **Configuration (`csr_scraper.py`):**
    *   Remove any hardcoded API keys from the standalone script logic during integration.
    *   Define constants or load environment variables near the top of `csr_scraper.py` for:
        *   `GROQ_API_KEY = os.environ.get("GROQ_API_KEY")`
        *   `GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")`
        *   `GOOGLE_SEARCH_ENGINE_ID = os.environ.get("GOOGLE_SEARCH_ENGINE_ID")`
    *   In the `main` function of `csr_scraper.py`, add checks to ensure these keys are not `None`, logging an error and exiting if they are missing.
    *   Define other relevant settings from the standalone scripts as constants in `csr_scraper.py` (e.g., `SEARCH_RESULTS_TO_PROCESS`, `SEARCH_SCRAPE_DEPTH`, `GROQ_MODEL_NAME`, `GROQ_MAX_LINKS_TO_SEND`, `PAGE_LOAD_TIMEOUT`, `REQUEST_TIMEOUT`, `FILE_SIZE_LIMIT`).

3.  **Refactor Finder Logic (Integrate into `csr_scraper.py`):**
    *   Define a new function `find_reports_with_groq(company: str, start_year: int, end_year: int) -> Dict[int, str]`.
    *   Copy the core logic from `standalone_report_finder2.py`'s `find_reports_standalone` function into this new function.
    *   Copy necessary helper functions (`normalize_text`, `is_pdf_url`, `extract_year`, `create_link`, `search_google_cse`, the scraping logic inside the loop, the filtering logic, the Groq analysis logic) into `csr_scraper.py`, making them private helpers (e.g., `_normalize_text`, `_search_google_cse`) or keeping them as nested functions if appropriate.
    *   Modify the copied `_search_google_cse` to use the configured `GOOGLE_API_KEY` and `GOOGLE_SEARCH_ENGINE_ID`.
    *   Modify the copied Groq interaction logic to use the configured `GROQ_API_KEY` and `GROQ_MODEL_NAME`.
    *   Adapt all logging calls within the copied logic to use `csr_scraper.py`'s existing `write_log` function. Remove `loguru` setup specific to the standalone script.
    *   Ensure the Selenium WebDriver logic within this function remains self-contained (it initializes and quits its own driver for the scraping part) as it does in the standalone script. Use the configured Chrome options.
    *   Ensure the function returns a dictionary mapping the *integer* year to the best URL string found (e.g., `{2023: "url1", 2022: "url2"}`). Handle the case where Groq analysis fails or returns no results by returning an empty dictionary.

4.  **Refactor Downloader Logic (Integrate into `csr_scraper.py`):**
    *   Define a new function `download_pdf_robustly(url: str) -> Optional[bytes]`.
    *   Copy the core logic from `standalone_pdf_downloader.py`'s `download_pdf_standalone`, `_direct_download`, and `_selenium_download` functions into this new function.
    *   Copy necessary helper functions (`_is_valid_pdf`, `get_parent_url`, `create_browser_options`, `get_webdriver`, `navigate_to_url`) into `csr_scraper.py` as private helpers (e.g., `_is_valid_pdf_download`, `_get_webdriver_downloader`).
    *   Initialize the `requests.Session` (`GLOBAL_SESSION` in the standalone script) once globally within `csr_scraper.py` or ensure it's properly managed within the downloader function. Use the configured User-Agent.
    *   Ensure the Selenium options (e.g., `CHROME_OPTIONS_DICT`) and timeouts used by the downloader logic are sourced from the configuration constants defined in step 2.
    *   Adapt all logging calls within the copied logic to use `write_log`. Remove `loguru` setup.
    *   Ensure the function returns the PDF content as bytes if successful, otherwise `None`.

5.  **Modify `csr_scraper.py` Core Workflow:**
    *   Delete the original `get_search_results` function.
    *   Delete the original `init_driver` function (as driver handling is now within the finder/downloader logic if needed).
    *   Modify `search_and_process(company_name)`:
        *   Remove the `driver = init_driver()` call and the `finally: driver.quit()` block.
        *   Set `start_year = 2020`, `end_year = 2024` (or make these configurable).
        *   Call the new finder: `found_reports: Dict[int, str] = find_reports_with_groq(company_name, start_year, end_year)`.
        *   If not `found_reports`, log a message for the company and return.
        *   Iterate through `year, url` in `found_reports.items()`.
        *   **Inside the loop:**
            *   Perform the MongoDB check: `existing = mongo_db["csr_reports"].find_one({"company_name": company_name, "csr_report_year": year})`. If `existing`, `write_log(...)` and `continue`.
            *   Call the new downloader: `pdf_bytes: Optional[bytes] = download_pdf_robustly(url)`.
            *   If `pdf_bytes`:
                *   Create a temporary file path using `tempfile` module or a simple naming convention (e.g., `./temp_pdf_{company_name}_{year}.pdf`). Ensure the directory exists (`os.makedirs("./temp_pdfs", exist_ok=True)`).
                *   Save the downloaded `pdf_bytes` to this temporary path (`temp_pdf_path`).
                *   Call the existing `upload_to_minio(company_name, year, temp_pdf_path)`. Store the returned `obj_name`.
                *   If `obj_name` is not `None`: Call the existing `save_csr_report_info_to_mongo(company_name, url, obj_name, year)`.
                *   Use a `finally` block or `try...finally` around the upload/save steps to ensure the temporary file is deleted: `if os.path.exists(temp_pdf_path): os.remove(temp_pdf_path)`.
            *   Else (if `pdf_bytes` is `None`): `write_log(f"Failed to download PDF for {company_name} {year} from {url}")`.
    *   No changes should be needed for `process_batch` or the main structure of `main` (other than the API key checks).

6.  **Update Documentation (`code_explained.md`):**
    *   Modify Section 4 (`modules/scraper/csr_scraper.py`) to accurately describe the new workflow:
        *   Mention fetching companies from Postgres.
        *   Explain the call to `find_reports_with_groq`, summarizing its use of Google CSE, optional scraping, filtering, and Groq analysis.
        *   Describe the iteration over found reports, the MongoDB check.
        *   Explain the call to `download_pdf_robustly`, summarizing its direct HTTP attempt and Selenium/XHR fallback.
        *   Detail the temporary file saving, MinIO upload, MongoDB metadata storage, and temporary file cleanup.
    *   Update the configuration section to include the new API keys and settings.
    *   Remove descriptions of the old Bing search (`get_search_results`) and simple `requests` download (`download_pdf`).
    *   Append this plan under the new "15. Integration Plan" heading.

7.  **Testing:**
    *   After implementation, run `python main.py scrape --max-companies 1` (or a small number) to test the end-to-end flow for a few companies.
    *   Verify logs for correct API calls (CSE, Groq), successful downloads (direct or Selenium), uploads to MinIO, and metadata creation in MongoDB.
    *   Check error handling for missing API keys, failed searches, failed downloads, etc. 