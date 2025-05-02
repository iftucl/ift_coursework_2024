
# 📑 ESG-AI: An End-to-End LLM-Driven Extraction & Analytics Pipeline  
**Team Magnolia** | IFTE 0003 Big Data in Quantitative Finance (2024/25)  
**Authors:** Neil Anderson · Magical Starmac · Rachel Hu · Tong Zhang  
**Supervisor:** Dr. Luca Cocconcelli  

---

## 0 · Executive Summary  
**Challenge:** Corporate sustainability (ESG) disclosures are buried in unstructured PDFs that vary by layout, language, and reporting standard.  
**Solution (ESG-AI):**  
1. **Ingest** PDFs from a MinIO data lake.  
2. **Filter** ESG-relevant pages via theme-specific regex detectors.  
3. **Parse** pages to Markdown with Docling + TableFormer (OCR + table recovery).  
4. **Extract** raw metrics & commitments with a first-pass Groq LLM prompt per theme.  
5. **Refine** and standardize all themes in a single second-pass LLM call (model cascade fallback).  
6. **Persist** structured records into both MongoDB (document store) and PostgreSQL (star schema).  
7. **Serve** an interactive Flask dashboard for data exploration.  
8. **Automate** via CLI, batch mode, scheduler integration, and CI/CD with test coverage ≥ 80 %.

This README details the rationale, design, installation, usage, testing, deployment, and future roadmap—providing a blueprint for a production-grade ESG data product.

---

## 1 · Motivation & Context  

| Driver                                    | Description                                                                                   | Impact                                                       |
|-------------------------------------------|-----------------------------------------------------------------------------------------------|--------------------------------------------------------------|
| **Regulatory Mandates**                   | New standards (CSRD EU, SEC climate rules) require granular ESG disclosures.                  | Organizations must report dozens of KPIs; manual methods fail. |
| **Analyst Bottlenecks**                   | Traditional copy-paste → spreadsheets pipelines introduce transcription errors and delays.    | Slows investment decisions; undermines trust in data.        |
| **Scalability**                           | Hundreds of global firms, annual reports → manual pipelines cannot scale                     | Need automated, robust, extensible extraction.               |
| **Multi-format Variability**              | Scanned vs. born-digital, tables vs. narrative, languages, formatting inconsistencies.        | Extraction logic must adapt to heterogeneity.                |
| **Audit & Lineage Requirements**          | Research and compliance need traceable provenance for every data point.                      | Must record page numbers, source tables, extraction logs.    |

---

## 2 · Research Contributions  

1. **Theme-aware Page Filtering**  
   - Regex libraries for 8 sustainability themes (GHG, Energy, Water, Waste, Biodiversity, Circularity, Social, Governance).  
   - Multi-criteria: units, keyword hits, year occurrences.  
   - Fallback mechanism: retains full PDF if no pages match.  

2. **Docling + TableFormer Conversion**  
   - Leverages layout-aware OCR to extract text and detect table structures.  
   - Pre- and post-processing ensures consistent Markdown with page delimitation.  

3. **Two-Stage LLM Extraction Architecture**  
   - **Pass 1 (Theme-wise):** Smaller prompts per theme → reduces JSON 5XX errors.  
   - **Pass 2 (Global Refinement):** Single consolidated payload standardized by cascade of models to guarantee schema conformance.  
   - JSON5 parsing fallback for resilient JSON handling.

4. **Dual-Store Persistence**  
   - **MongoDB:** Fine-grained document store (`csr_reports`) for flexible queries and lineage.  
   - **PostgreSQL:** Star schema (`company_dim`, `indicator_dim`, `csr_indicators`, `csr_commitments`) for OLAP and dashboarding.

5. **Interactive Visualization Dashboard**  
   - Flask app with four views: quick time series, data coverage, search table, and dynamic charting (AJAX endpoints).  
   - Runtime launched via `Main.py serve`, zero additional config.  

6. **End-to-End Automation & CI/CD**  
   - **CLI:** `extract`, `batch-extract`, `convert`, `show-*`, `serve`.  
   - **Scheduling:** Supports `--frequency` for APScheduler or cron integration examples.  
   - **Testing:** Pytest suite with unit, integration, e2e tests; coverage enforced ≥ 80 %.  
   - **Quality:** Pre-commit hooks (Black, isort, Flake8, Bandit, Safety).  
   - **CI:** GitHub Actions runs lint, security scans, and tests on every PR.

---

## 3 · High-Level Architecture  

```mermaid
flowchart LR
  subgraph A [Data Lake]
    A1[MinIO Bucket ‹csr-reports›]  
  end
  subgraph B [Orchestrator]
    B1[CLI: batch.py → run_batch] 
    B2[Main.py extract/batch-extract]
  end
  A1 -- list_objects --> B1
  B1 -- download_pdf(key) --> B2
  B2 --> C[FitZ filter_pdf]
  C --> D[Docling → Markdown]
  D --> E1[LLM Pass 1 per theme]
  E1 --> E2[LLM Pass 2 global refine]
  E2 --> F1[MongoDB ingest_report]
  E2 --> F2[PostgreSQL batch_insert_*]
  F1 --> G[Flask Dashboard <http>]
  style B1 fill:#e8f4fc,stroke:#1a76d2
  style G fill:#fff3e0,stroke:#fb8c00
```

---

## 4 · Detailed Design  

### 4.1 · Configuration (`config/conf.yaml`)  
- **MinIO**: `endpoint`, `access_key`, `secret_key`, `bucket`.  
- **Groq LLM**: primary/fallback models, API key, base URL.  
- **Themes**: unit regex, keywords, year rules for each theme.  
- **Output filenames** and **MinIO fallback PDF path**.

### 4.2 · Extractor Module (`modules/extract/extractor.py`)  
- `filter_pdf(src, dst)`: returns matched page indices, theme flags, labels.  
- `parse_with_docling(...)`: leverages `docling.document_converter` with TableFormer.  
- `_batches(...)`: dynamically splits pages to respect token limits.  
- `llm_extract`: robust two-model retry with JSON5 fallback.  
- `extract_md` & `refine_extracted`: orchestrate first and second pass.

### 4.3 · Persistence Layer  

#### MongoDB (`modules/db/ingest.py`)  
- Cleans & validates with `modules.extract.validator`.  
- Enriches with `company_id`, `company_name`, `ingested_at`, `sub_category`, etc.  
- Inserts into `csr_reports` collection.

#### PostgreSQL (`modules/db/pg_client.py` + ingest sync)  
- `company_dim`, `indicator_dim` upserts via `ON CONFLICT`.  
- `csr_indicators`, `csr_commitments` batch inserts with `psycopg2.extras.execute_values`.  
- Deployed schema in `modules/Schema.sql` (idempotent).

### 4.4 · CLI & Orchestration (`Main.py`)  
Sub-commands:  
- `extract`: full pipeline → JSON → DB.  
- `batch-extract`: loops MinIO keys.  
- `convert`: JSON → flattened CSV.  
- `serve`: launches Flask dashboard.  
- `show-*`: catalog, dictionary, lineage, report.

### 4.5 · Visualization (`modules/Viz/app.py`)  
- **Routes**: `/`, `/datacheck`, `/search`, `/dataviz` + AJAX APIs.  
- **Data loading**: on-startup Mongo query → in-memory list.  
- **Templates**: Jinja2 for dropdowns, tables, chart placeholders.  
- **Static assets**: D3.js / Chart.js for plotting.

### 4.6 · Scheduling & Automation  
- CLI supports `--frequency` (daily/weekly/monthly).  
- Example APScheduler integration in `deploy/scheduler.py`.  
- Cron examples in `deploy/cron_jobs.sh`.

---

## 5 · Installation & Quickstart  

### 5.1 · Prerequisites  
- **Docker** & **Docker Compose**  
- **Poetry** (≥ 1.4)  
- **Python** 3.10–3.12  

### 5.2 · Clone & Dependencies  

```bash
git clone https://github.com/iftucl/ift_coursework_2024.git
cd ift_coursework_2024/team_magnolia/coursework_two
poetry install --with dev
poetry shell
```

### 5.3 · Infrastructure  

```bash
docker compose -f deploy/compose.yml up -d
# Services:
#  - mongo_db_cw  @ localhost:27019
#  - minio         @ localhost:9000
#  - postgres_db_cw@ localhost:5439
```

### 5.4 · Environment Variables  

Copy `.env.sample → .env` and edit:

```ini
GROQ_API_KEY=sk-…
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=ift_bigdata
MINIO_SECRET_KEY=minio_password
MONGO_URI=mongodb://localhost:27019
MONGO_DB=csr_extraction
POSTGRES_URI=postgresql://postgres:postgres@localhost:5439/fift
POSTGRES_SCHEMA=csr_reporting
```

Load:

```bash
source .env
```

---

## 6 · Usage  

### 6.1 · Single-report Extraction  

```bash
python Main.py extract \
  --minio-key "2024/Apple Inc..pdf"
```

**Output:**  
- `output/filtered_report_pages.pdf`  
- `output/filtered_report_parsed.md`  
- `output/extracted_data.json`  
- `output/final_standardized.json`  
- Mongo documents + Postgres rows  

### 6.2 · Year-prefix Batch  

```bash
python Main.py batch-extract \
  --prefix "2024/" \
  --limit 20
```

### 6.3 · JSON→CSV  

```bash
python Main.py convert \
  --json_file output/final_standardized.json \
  --csv_file  output/standardized_data.csv
```

### 6.4 · Launch Dashboard  

```bash
python Main.py serve --host 0.0.0.0 --port 5000
```

Open your browser at <http://localhost:5000>.

### 6.5 · Other Commands  

```bash
python Main.py show-catalogue
python Main.py save-catalogue
python Main.py show-dictionary
python Main.py show-lineage
python Main.py show-report --company_id 680c06cb… --year 2024
python Main.py ingest --json_file output/final_standardized.json
```

---

## 7 · Testing & Quality Assurance  

```bash
# 1) Static checks
pre-commit run --all-files

# 2) Run tests & coverage
pytest --maxfail=1 --disable-warnings -q --cov=modules

# 3) Coverage badge → target ≥ 80%
```

**Test coverage breakdown**  
- **Unit**: `_match_theme`, `_safe_eval`, `_clean_numeric`, pg_client upserts.  
- **Integration**: `filter_pdf` + `parse_with_docling` (using small sample PDF).  
- **End-to-end**: `Main.py extract` on dummy PDF → graceful failure path.

**CI/CD**  
- `.github/workflows/ci.yml` defines GitHub Actions to install, lint, security-scan (Bandit/Safety), and run tests.  
- PRs blocked if any check fails or coverage dips below threshold.

---

## 8 · Deployment & Docker  

### 8.1 · CW-2 Dockerfile (deploy/Dockerfile)  

```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY poetry.lock pyproject.toml /app/
RUN pip install poetry \
 && poetry config virtualenvs.create false \
 && poetry install --no-dev --no-interaction

COPY . /app

EXPOSE 5000 8000

CMD ["python", "Main.py", "serve", "--host", "0.0.0.0", "--port", "8000"]
```

### 8.2 · Compose Integration  

```yaml
services:
  cw2:
    build: ./deploy
    ports:
      - "8000:8000"
    env_file: .env
    depends_on:
      - mongo_db_cw
      - postgres_db_cw
      - minio
```

After `docker compose up --build`, your entire stack (DBs + CW2 API + dashboard) is live in one command.

---

## 9 · Observability & Resilience  

1. **Structured logging** via Python `logging` (JSON format) at DEBUG/INFO/WARN/ERROR levels.  
2. **Metrics endpoint** (`/metrics`) for Prometheus:  
   - `esgai_llm_calls_total`  
   - `esgai_llm_failures_total`  
   - `esgai_processed_reports_total`  
3. **Retry strategy** for LLM calls via `tenacity` exponential back-off.  
4. **Failed JSON dumps** persisted under `output/failed_llm/` for later analysis.

---

## 10 · Limitations & Future Work  

| Limitation                                      | Future Work                                         |
|-------------------------------------------------|-----------------------------------------------------|
| OCR errors on low-quality scans                 | Integrate domain-specific OCR training              |
| LLM hallucinations on edge cases                | Add external retrieval (RAG) for context enrichment |
| Single-node processing                          | Migrate to distributed pipeline (Kafka + Airflow)   |
| In-memory dashboard data                        | Lazy-load / pagination for large corpora            |
| Static schema mapping                           | Schema versioning & automated migrations            |

---

## 11 · Acknowledgements & References  

1. **Groq Llama-4 API** documentation & research credits  
2. **Docling** & **TableFormer** teams for layout parsing  
3. **IFTE BBU** course materials & teaching team  
4. **GRI Standards**, **GHG Protocol** for ESG taxonomy  

---

## 12 · License  

Distributed under the **MIT License** © 2025 Team Magnolia — “Automate once, analyse perpetually.”  
```