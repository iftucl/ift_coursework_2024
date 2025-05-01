# CW2 Project: CSR Report Processing Pipeline

This project implements an automated pipeline to download, process, and extract ESG-related data (Scope 1, 2, 3 emissions and Water Consumption) from corporate CSR reports. The extracted data is normalized and stored back into a PostgreSQL database. An interactive HTML dashboard is also included. Documentation is auto-generated using Sphinx.

---

## Directory Structure
```
coursework_two/
├── docs/                      # Sphinx documentation
│   ├── source/                # .rst files and conf.py
│   └── _build/                # Generated HTML docs
├── downloads/                # Temporary folder for downloaded PDFs
├── modules/                  # Core logic modules
│   ├── api.py                # (Optional) API related helpers (currently unused)
│   ├── config.py             # Config: DB credentials and DeepSeek API
│   ├── db.py                 # DB connection, table creation, data update
│   └── output.py             # Main processing: download, extract, update
├── main.py                   # CLI menu and entry point
├── pyproject.toml            # Poetry configuration
├── poetry.lock               # Poetry lock file
├── gai.html                  # Interactive ESG data dashboard
└── test/                     # Contains unit tests and integration tests
```

---

## Modules Description

- **main.py**: CLI interface to initialize the database and run the full pipeline.
- **modules/db.py**: PostgreSQL connection and schema setup, updates extracted indicators.
- **modules/output.py**: Core logic: fetch reports, download PDFs, extract content using DeepSeek API, write back results.
- **modules/config.py**: Stores DB credentials and DeepSeek API key/url.
- **gai.html**: A dashboard to explore Scope 1, 2, 3 and Water metrics with filter/search/chart functions.
- **test/**: Contains test cases for different components, including:
  - `test_end_to_end.py`: End-to-end test for the entire pipeline
  - `test_pipeline/`, `test_unit/`: Submodules for pipeline logic and unit testing

---

## Workflow

1. Load CSR `report_url` and `report_year` from the PostgreSQL table `ginkgo.csr_reports_with_indicators`.
2. Try downloading the PDF using `requests` (fallback to Selenium if needed).
3. Extract PDF pages that mention "Scope 1", "Scope 2", etc.
4. Submit the text to DeepSeek API for structured extraction.
5. Parse response and normalize units: emissions to `tCO2`, water to `Mgal`.
6. Update the original database with these standardized values.

---

## Installation

```bash
poetry install
```

Make sure PostgreSQL is running. Update credentials in `modules/config.py`.

---

## Usage

Basic testing functionality is included under the `test/` folder. See its internal README for details on unit tests and end-to-end pipeline tests.


Run from project root:

```bash
poetry run python main.py
```

Choose from the following menu:

```
1. Initialize table structure
2. Run CSR report processing
3. Run all
0. Exit
```

---

## DeepSeek API Input/Output

- **Prompt**: PDF content containing ESG metrics
- **Expected Output**:
```json
{
  "scope_1": 1234.5,
  "scope_2": 678.9,
  "scope_3": 321.0,
  "water_consumption": 45.6
}
```
- **Normalization**:
  - Emissions converted to `tCO2`
  - Water converted to `Mgal`

---

## Documentation (Sphinx)

Generate HTML documentation:

```bash
cd docs
sphinx-build -b html source _build/html
```
Then open in browser:

```bash
open docs/_build/html/index.html
```

---

## How to View the HTML Dashboard (`gai.html`)

1. Ensure your backend API is running and accessible at `http://localhost:8000/reports`
   - This API should return the `csr_reports_with_indicators` table in JSON format.

2. Open the dashboard:

```bash
open gai.html
```

Or simply drag and drop the file into your browser.

3. Features include:
   - Company search and filtering
   - Year dropdown filter
   - Switchable bar and trend charts
   - Export to PDF / Word

> If you encounter "failed to fetch data", ensure the API server is up and CORS is configured correctly.

---

