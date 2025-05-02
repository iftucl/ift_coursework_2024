
---

## 📄 Project README 
# End-to-End Data Product Development for CSR Indicators: Extraction, Storage, and Visualization

---

## Project Overall Process
![Project Overall Process](https://raw.githubusercontent.com/Etainos/ift_coursework_2024/team_jacaranda/team_jacaranda/coursework_two/static/Project_Process.jpg)

---
## ⚡ Quick Start

Run the entire stack with:

```bash
docker compose up --build
```

> Then, access the frontend at: [https://csr.jacaranda.ngrok.app/](https://csr.jacaranda.ngrok.app/)

![Frontend Page](https://raw.githubusercontent.com/Etainos/ift_coursework_2024/team_jacaranda/team_jacaranda/coursework_two/static/Frontend_Page_1.jpg)
![Frontend Page](https://raw.githubusercontent.com/Etainos/ift_coursework_2024/team_jacaranda/team_jacaranda/coursework_two/static/Frontend_Page_2.jpg)

---

## 📌 Project Overview
This project delivers an **end-to-end data product** for CSR indicators, covering:

- Extraction of sustainability (CSR) indicators from corporate reports
- Standardized storage in a database
- Visualization via a frontend interface

All components are fully containerized, with backend dependencies managed by **Poetry**.

## 📌 Project Abstract:
This project delivers a robust and modular platform for extracting, standardizing, and visualizing Corporate Social Responsibility (CSR) data from PDF reports. The system combines a high-performance FastAPI backend with a responsive React frontend, underpinned by a structured PostgreSQL database and supported by cloud-based object storage (MinIO). Sustainability indicators are automatically identified through keyword-based paragraph extraction and refined using large language models (LLMs) for accurate value recognition and unit standardization. The pipeline is orchestrated end-to-end and thoroughly tested using pytest, with test coverage exceeding 80% for backend modules. Due to the frontend being developed in JavaScript, structural validation is performed via Python-based static tests to comply with testing requirements. Security analysis with Bandit and Safety confirms strong hygiene across all components, with actionable findings mainly localized to data ingestion scripts. The final system enables efficient ESG data querying, reporting, and comparison at scale, making it a valuable foundation for sustainability analytics.

---

## ⚙️ Environment Requirements
- Docker & Docker Compose
- Poetry ≥ 1.5.0
- Node.js ≥ 16.0 (for frontend development)
- Python ≥ 3.8 (managed via Poetry)
- PostgreSQL (in container)
- MinIO storage service (in container)

---

## 📂 Project Structure
```
coursework_two/
 ├── config/                  # Configuration folder.
 ├── docs/                    # Documentation folder, contains reStructuredText source files and Sphinx configuration for generating project documentation.
 ├── my_fastapi/              # Backend API (FastAPI service), responsible for handling frontend requests and providing data endpoints.
 ├── modules/
 │    ├── data_storage/       # Data extraction and processing module, responsible for extracting data from various sources and preprocessing it.
 │    ├── db/                 # Output data folder, stores processed data files for preview.
 │    ├── frontend/           # Frontend React application, displays data and interacts with the user.
 │    ├── security/           # Security module, involves authentication, authorization, and data protection functionalities.
 │    └── __init__.py         # Marks this folder as a Python module.
 ├── static/                  # Static assets folder, contains static files needed by the frontend (e.g., images).
 ├── test/                    # Test scripts folder, contains unit tests and integration tests, etc.
 ├── security_report/         # Bandit and Safety security scan report.
 ├── .env                     # Environment variables file, stores configuration for the project environment.
 ├── Dockerfile.txt           # Dockerfile, defines how to build the Docker image for the project.
 ├── pyproject.toml           # Poetry dependency configuration file, lists the Python packages required for the project.
 ├── poetry.lock              # Poetry lock file, records the exact versions of dependencies.
 ├── pytest.ini               # Pytest configuration file, defines options for running tests.
 └── .gitignore               # Git ignore file, lists files that should not be tracked by version control.
```

---

## 🚀 Deployment & Startup Guide

### 1. Clone the Project
```bash
git clone -b team_jacaranda https://github.com/Etainos/ift_coursework_2024.git
cd coursework_two
```

### 2. Install Python Dependencies via Poetry
```bash
poetry install
```

### 3. Configure Environment Variables
Create a `.env` file:
```
DEEPSEEK_API_KEY = sk-f3***************
```

### 4. Build and Start Containers
```bash
docker compose up --build
```

---

## 🛠️ Backend Data Processing Workflow

Activate the Poetry environment and run:

```bash
poetry shell
```

Execute step-by-step scripts:
```bash
poetry run python modules/data_storage/create_table.py
poetry run python modules/data_storage/paragraph_extraction.py
poetry run python modules/data_storage/retry_failed_reports.py
poetry run python modules/data_storage/llm_analyse.py
poetry run python modules/data_storage/llm_standardize.py
poetry run python modules/data_storage/data_export.py
```
Or run the full pipeline with:
```bash
poetry run python modules/data_storage/main.py
```

---

## 🔗 Backend API (FastAPI)

Start the FastAPI server:
```bash
poetry run uvicorn FastAPI.main:app --reload --host 0.0.0.0 --port 8000
```

---

## 🎨 Frontend Development and Production Build

### Development Mode
```bash
cd modules/frontend
npm install
npm start
```
Access the frontend at: [https://csr.jacaranda.ngrok.app/]

### Production Build
```bash
npm run build
```

---

## ✨ Project Highlights
- 📑 End-to-end pipeline: PDF extraction ➔ Indicator extraction ➔ Unit standardization ➔ Database storage ➔ Frontend visualization
- ⚡ LLM-enhanced intelligent processing (text understanding and unit standardization)
- 🐳 Fully containerized deployment for maximum environment consistency
- 📦 Centralized dependency management via Poetry
- 🔍 Full test coverage with pytest

---
