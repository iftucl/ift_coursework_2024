# **CSR Data Pipeline & Data Lake**

**Author**: *Magnolia*  
**Version**: 1.0.0  
**License**: MIT (or your choice)

This repository automates the **scraping**, **cleaning**, **storage**, **retrieval**, and **analysis** of Corporate Social Responsibility (CSR) reports. We use **Selenium**, **MongoDB**, **MinIO**, **PostgreSQL**, and **FastAPI** to ensure a robust, maintainable, and highly scalable system.

---

## **Table of Contents**
1. [Overview](#overview)
2. [Directory Structure](#directory-structure)
3. [Installation](#installation)
4. [Configuration](#configuration)
5. [Usage](#usage)
   - [Main Subcommands](#main-subcommands)
   - [Scripts](#scripts)
6. [Data Lake Design](#data-lake-design)
7. [Running the System](#running-the-system)
8. [Code Quality & Testing](#code-quality--testing)
9. [Troubleshooting](#troubleshooting)
10. [Contributing](#contributing)
11. [License](#license)

---

## **1. Overview**

In a world increasingly focused on **ESG metrics**, the timeliness and accuracy of **CSR reports** matter greatly to stakeholders, researchers, and data scientists. **CSR Data Pipeline** aims to:

- **Scrape** thousands of CSR PDF reports from corporate websites or search engines.  
- **Clean & Validate** metadata (e.g., correcting out-of-range years, removing duplicates).  
- **Store** final PDF files in **MinIO** (S3-compatible) and metadata in **MongoDB** or **PostgreSQL**.  
- **Provide** a **FastAPI** endpoint to easily search and download these reports.  
- **Offer** an optional analysis layer (e.g. text extraction, sentiment checks).  
- Maintain high **code quality** using best practices (Black, Flake8, Pytest).

---

## **2. Directory Structure**

Below is the recommended layout (based on your final structure):

```
coursework_one/
├── config/
│   └── conf.yaml                # YAML configuration (e.g. credentials, environment)
│
├── modules/
│   ├── __init__.py              # Makes 'modules' a Python package
│   ├── api/
│   │   ├── analysis_pipeline.py # Analysis logic (text extraction, sentiment)
│   │   ├── fastapi_api.py       # FastAPI server
│   │   ├── mongo_index_setup.py # Script to create MongoDB indexes
│   │   └── streamlit_app.py     # (Optional) A Streamlit UI
│   │
│   ├── db/
│   │   ├── __init__.py
│   │   └── db_connection.py     # PostgreSQL or MongoDB connection utilities
│   │
│   ├── minio_ops/
│   │   ├── minio_client.py      # MinIO client logic
│   │
│   └── scraper/
│       ├── reports/             # Downloaded PDF reports
│       ├── temp_reports/        # Temporary or staging files
│       ├── csr_extractor.log    # Logs from extraction
│       ├── csr_fast.log         # Additional logs
│       ├── csr_fix_and_cleanup.log
│       ├── csr_fix_and_cleanup.py # Fix script (year correction, duplicates removal)
│       └── csr_scraper.py       # Core scraping logic
│
├── pyproject.toml               # Python packaging config, dependencies
├── poetry.lock                  # If using Poetry
├── scripts/
│   ├── run_api.sh               # Shell script to run the API
│   └── run_scraper.sh           # Shell script to run the scraper
│
├── static/
│   # (Potentially for images/CSS/JS if Streamlit or other frontends)
│
├── test/
│   ├── conftest.py
│   ├── test_csr_scraper.py      # Pytest for the scraper
│   └── test_fastapi_api.py      # Pytest for FastAPI
│
├── docker-compose.yml           # Orchestrates DBs, MinIO, Kafka, etc.
├── main.py                      # Project entry script with argparse subcommands
├── README.md                    # This documentation
└── scraper_cron.log            # Logs from cron-based scraping (optional)
```

**Key Modules**:  
- `csr_scraper.py` (scraping pipeline)  
- `csr_fix_and_cleanup.py` (cleaning tasks)  
- `analysis_pipeline.py` (analysis tasks)  
- `fastapi_api.py` (FastAPI server)  
- `mongo_index_setup.py` (MongoDB indexes)

---

## **3. Installation**

1. **Clone** this repository:
   ```bash
   git clone https://github.com/yourusername/csr_data_project.git
   cd coursework_one
   ```
2. **Install dependencies** using Poetry (defined in `pyproject.toml`):
   ```bash
   pip install poetry  # If you don't have poetry
   poetry install
   ```
3. (Optional) **Activate a virtual environment**:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install .
   ```
4. **Check**:
   ```bash
   poetry run python main.py --help
   ```

---

## **4. Configuration**

- **Environment Variables**: Settings like database URIs (`MONGO_URI`), MinIO host (`MINIO_HOST`), and Docker detection (`DOCKER_ENV`) are read from environment variables. Defaults are often provided in the code.
- **docker-compose.yml**: Orchestrates service containers (`mongo_db`, `postgres_db`, `miniocw`, `pgadmin`, `selenium`, `magnolia_scraper`, etc.) and sets necessary environment variables for containerized execution.

---

## **5. Usage (CLI Reference)**

All functionality is exposed through `main.py` subcommands:

```bash
poetry run python main.py [command] [options]
```

* **`scrape [--max-companies N]`**  
  Scrape CSR reports. Optional parallelism via `CSR_MAX_WORKERS` (capped at 4). The scraper automatically decides whether to use a remote Selenium grid (if `SELENIUM_URL` is set) or fall back to a *local* Chrome/Chromedriver when you pass `--local-selenium`.
  ```bash
  # Example: Scrape 20 companies
  poetry run python main.py scrape --max-companies 20
  ```

* **`analysis [--quick]`**  
  ```bash
  # Example: Run analysis (if enabled)
  # poetry run python main.py analysis --quick
  ```
  **Note:** This command is currently *commented out* in `main.py`. The code exists in `modules/api/analysis_pipeline.py`.

* **`fix [--dry-run]`**  
  Clean up metadata (year correction, duplicates).
  ```bash
  # Example: Preview changes without applying
  poetry run python main.py fix --dry-run
  ```

* **`index`**  
  Create/update MongoDB indexes.
  ```bash
  poetry run python main.py index
  ```

* **`api [--host HOST] [--port PORT] [--reload]`**  
  Launch FastAPI server.
  ```bash
  poetry run python main.py api --host 0.0.0.0 --port 8000 --reload
  ```

* **Dashboard**  
  ```bash
  # Streamlit UI (requires API running)
  poetry run streamlit run modules/api/streamlit_app.py
  ```

* **Scheduler**  
  ```bash
  # Run scrape every 7 days
  python -c "from modules.scraper.csr_scraper import schedule_scraper; schedule_scraper()"
  ```

### **Scripts**

- **`run_api.sh`**: Utility script for starting the FastAPI server.
- **`run_scraper.sh`**: Utility script for running the scraper.

---

## **6. Data Lake Design**

We implement an **S3-like data lake** in MinIO:

- **Raw Zone**:
  ```
  minio
  └── csreport/  
      ├── 2023/
      │   ├── Apple_Inc.pdf
      │   └── ...
      ├── 2024/
      │   ├── ...
      ...
  ```
- **Metadata in MongoDB** or **PostgreSQL**:
  - `company_name`
  - `csr_report_year`
  - `storage_path`
  - `ingestion_time`
  - (etc.)

When you query **FastAPI**:
1. The code looks up metadata in MongoDB/Postgres.  
2. Fetches the real PDF path from MinIO if needed.  
3. Returns results to the user or a bulk ZIP download.

---

## **7. Running the System**

You have two main options for spinning up infrastructure and running the CLI commands (see [Section 5](#usage-cli-reference)):

### **Option 1: Full-Docker Mode**
This will start **all** infra containers *and* an idle `magnolia_scraper` application container. You then `docker exec` into that container to kick off scrapes, fix jobs, the API, etc.

1. From the repo root (where `docker-compose.yml` lives):
   ```bash
   cd /path/to/coursework_one
   docker compose up -d
   ```

**Containers launched**:
- `mongo_db` → MongoDB on 27019
- `postgres_db` → PostgreSQL on 5439
- `postgres_seed` → Seeds initial company list
- `pg_admin_cw` → pgAdmin on 5051
- `miniocw` → MinIO server on 9000/9001
- `minio_client_cw` → Creates/configures MinIO bucket
- `selenium` → Selenium Grid on 4444 (optional)
- `magnolia_scraper_cw` → Idle application container (runs sleep infinity)

**Run one-off tasks by exec'ing in**:
```bash
# Full scrape of _all_ companies
docker exec magnolia_scraper_cw poetry run python main.py scrape

# Control parallel workers (e.g. 4)
docker exec -e CSR_MAX_WORKERS=4 magnolia_scraper_cw \
  poetry run python main.py scrape

# Limit companies (e.g. 5)
docker exec magnolia_scraper_cw \
  poetry run python main.py scrape --max-companies 5

# Data cleanup (fix)
docker exec magnolia_scraper_cw poetry run python main.py fix

# Dry-run cleanup
docker exec magnolia_scraper_cw poetry run python main.py fix --dry-run

# Create MongoDB indexes
docker exec magnolia_scraper_cw poetry run python main.py index

# Launch FastAPI (detached)
docker exec -d magnolia_scraper_cw poetry run python main.py api
# → available at http://localhost:8000 (per compose port mapping)

# Schedule scraper every 7 days (detached)
docker exec -d magnolia_scraper_cw \
  poetry run python -c "from modules.scraper.csr_scraper import schedule_scraper; schedule_scraper()"
```

**To tail logs**:
```bash
docker compose logs -f magnolia_scraper_cw
docker compose logs -f mongo_db
# etc.
```

### **Option 2: Local-Dev Mode**
Run only the databases and MinIO in Docker, but execute Python code locally.

in SCR scraper     # options.add_argument("--headless=new")  # Must not be selected when running locally
**Start infra containers without the application**:
```bash
cd /path/to/coursework_one
docker compose up -d mongo_db postgres_db postgres_seed pg_admin_cw miniocw minio_client_cw
# Optional: if you prefer remote Selenium instead of a local Chrome:
docker compose up -d selenium
```

**Verify**:
- MongoDB → `mongodb://localhost:27019`
- PostgreSQL → `postgres://postgres@localhost:5439/postgres`
- MinIO Console→ `http://localhost:9001` (user `ift_bigdata` / `minio_password`)
- pgAdmin → `http://localhost:5051`

**Install Poetry & dependencies locally**:
```bash
pip install poetry
poetry install
```

**Run commands on your host machine**:
```bash
# Scrape (use --local-selenium to explicitly use local Chrome/Chromedriver)
poetry run python main.py scrape --local-selenium

# Limit to 5 companies, using local Selenium
poetry run python main.py scrape --max-companies 5 --local-selenium

# Or point at a remote Selenium Grid if available (do not use --local-selenium then)
# SELENIUM_URL=http://localhost:4444/wd/hub poetry run python main.py scrape

# Clean/fix
poetry run python main.py fix

# Create indexes
poetry run python main.py index

# FastAPI
poetry run python main.py api --host 127.0.0.1 --port 8000 --reload

# Scheduler (runs every 7 days)
poetry run python -c "from modules.scraper.csr_scraper import schedule_scraper; schedule_scraper()"

# Streamlit dashboard (needs API up)
poetry run streamlit run modules/api/streamlit_app.py
```
---

## **8. Code Quality & Testing**

1. **Formatting (Black)**  
   ```bash
   black .
   ```
2. **Linting (Flake8)**  
   ```bash
   flake8 .
   ```
3. **Testing (Pytest)**  
   ```bash
   pytest test/
   ```
   - `test_csr_scraper.py` checks scraping logic (Selenium calls, PDF downloads).  
   - `test_fastapi_api.py` verifies the API endpoints.

**Continuous Integration**: If using GitHub Actions, you can run all three steps on every pull request to keep the repo stable.

---

## **9. Troubleshooting**

1. **Scraper Times Out**  
   - Check if the remote site is blocking you. Possibly reduce concurrency or enable proxy usage in `csr_scraper.py`.

2. **MongoDB or MinIO Connection Error**  
   - Confirm correct environment variables.  
   - For Docker, verify the ports in your `docker-compose.yml` (e.g., `27019:27017` or `9000:9000`).

3. **API Returns 500**  
   - Inspect the logs in `csr_fast.log` or standard output. Possibly a missing PDF in MinIO or the year is out of the corrected range.

4. **Data Not Found in pgAdmin**  
   - In pgAdmin, add a server with `hostname=postgres_db`, `port=5432`, `username=postgres`, `password=postgres`.  
   - Make sure the container name references match.

---

## **10. Contributing**

We welcome **bug reports**, **feature requests**, and **pull requests**!  
- Fork the repo & create a feature branch.  
- Ensure you pass `black .`, `flake8 .`, and `pytest test/`.  
- Open a Pull Request describing your changes.

If you have questions, open an **issue** in this repository—happy to help!

---

## **11. License**

This project is distributed under the **MIT License** (or your chosen license). See the `LICENSE` file or `pyproject.toml` for more details.

---

**Thank you** for using the CSR Data Pipeline! If you run into any problems, feel free to create an issue or reach out. We hope this pipeline significantly eases the complexity of collecting, validating, and distributing CSR reports for your analyses. **Happy coding and data-lake building!**

---

## 📝 Note to self: Data stores & API cheat‑sheet

### MongoDB – `csr_db.csr_reports`
| field            | type / example                                           | notes                                      |
|------------------|----------------------------------------------------------|--------------------------------------------|
| `_id`            | `ObjectId("...")`                                        | auto‑generated                             |
| `company_name`   | `"Apple Inc."`                                           | text‑indexed                               |
| `csr_report_url` | original PDF URL                                         |                                            |
| `storage_path`   | `"2024/Apple Inc..pdf"`                                  | MinIO object key                           |
| `csr_report_year`| `2024`                                                   | integer                                    |
| `ingestion_time` | `"2025‑04‑21T10:17:34.812345"`                           | ISO‑8601 string                            |

Indexes  
* compound `{ company_name: 1, csr_report_year: 1 }` *(enforced unique in code)*  
* single `{ csr_report_year: 1 }`  
* text `{ company_name: "text" }`

---

### MinIO – bucket **`csreport`**

csreport/
└── {year}/
└── {Company}.pdf

*Every* PDF lives under its publication year.  
Bucket is public ⇒ `http://<host>:9000/csreport/{year}/{Company}.pdf`.

---

### FastAPI endpoints (port 8000 on `magnolia_scraper`)
| Method & path        | Purpose                             | Key params / body                                   |
|----------------------|-------------------------------------|-----------------------------------------------------|
| `GET /reports`       | Search CSR metadata in MongoDB.     | `company` (fuzzy), `year` (int)                     |
| `POST /download-zip` | Get a ZIP of selected PDFs.         | JSON `{ "report_paths": ["2024/Apple Inc..pdf", …]}`|

Example search:

```bash
cURL -G "http://localhost:8000/reports" \
     --data-urlencode "company=apple" \
     --data-urlencode "year=2024"

Response objects match the Mongo documents but include an extra field:

"download_link": "http://miniocw:9000/csreport/2024/Apple Inc..pdf"
```

Use those storage_path values in your /download-zip payload when you need multiple files at once.
---

#### First‑time setup reminder

After your initial **`scrape`** make sure to run these two commands so the database and indexes match the schema above and the API performs as expected:

```bash
poetry run python main.py fix    # cleans metadata: correct years, deduplicates, ISO‑formats timestamps
poetry run python main.py index  # builds the MongoDB indexes listed above
```

You only need to repeat `fix` and `index` after a fresh scrape or if you manually altered documents.

Add that to your README and you'll have a handy snapshot of the MongoDB schema, MinIO layout, and the key API calls.
