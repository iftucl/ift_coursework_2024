# CSR Indicators Data Product

## Overview
This project implements a comprehensive data product focused on Corporate Social Responsibility (CSR) indicators extracted from company CSR reports. Building upon the data lake constructed in Coursework One, this solution provides a structured, reliable, and scalable storage system for CSR indicators, enabling efficient data retrieval, validation, and analysis.

## Project Structure
```
team_Salix/coursework_two/
├── pipeline1/                  # Pipeline 1: Data Availability Check
│   ├── modules/               # Core implementation modules
│   │   ├── main.py           # Main pipeline execution
│   │   ├── pdf_checker.py    # PDF validation and checking
│   │   ├── process_problematic.py # Problematic file handling
│   │   └── __init__.py       # Package initialization
│   └── __init__.py           # Package initialization
│
├── pipeline2/                  # Pipeline 2: Content Extraction
│   ├── modules/               # PDF processing and extraction
│   │   ├── modelv2.py        # Content extraction model
│   │   └── __init__.py       # Package initialization
│   └── __init__.py           # Package initialization
│
├── pipeline3/                  # Pipeline 3: Storage Implementation
│   └── modules/               # Database operations
│       ├── write_lineage.py  # Data lineage tracking
│       └── write_to_db.py    # Database operations
│
├── pipeline4/                  # Pipeline 4: Visualization
│   ├── modules/               # Visualization components
│   │   ├── dashboard.py      # Dashboard implementation
│   │   └── __init__.py       # Package initialization
│   └── __init__.py           # Package initialization
│
├── config/                    # Configuration files
│   ├── pre-commit-config.yaml # Git pre-commit hooks configuration
│   ├── lin.json              # Lineage configuration
│   ├── test_config.yaml      # Test environment configuration
│   ├── scheduler_config.yaml # Task scheduling configuration
│   └── ref.json              # Reference data and mappings
│
├── docs/                      # Documentation
│   ├── build/                # Generated documentation
│   └── source/              # Documentation source
│
├── tests/                     # Test suite
│   ├── test_pipeline1/      # Tests for Pipeline 1
│   ├── test_pipeline2/      # Tests for Pipeline 2
│   ├── test_pipeline3/      # Tests for Pipeline 3
│   ├── test_pipeline4/      # Tests for Pipeline 4
│   ├── test_data/           # Test data and fixtures
│   ├── test_end_to_end.py   # End-to-end integration tests
│   └── conftest.py          # Test configurations and fixtures
│
├── .venv/                    # Python virtual environment
├── .gitignore               # Git ignore rules
├── .pre-commit-config.yaml  # Pre-commit hooks configuration
├── scheduler.py             # Task scheduling implementation
├── pyproject.toml           # Project dependencies and configuration
├── poetry.lock             # Locked dependencies
└── README-COURSEWORK_TWO.md # Project documentation
```

## Features

### Pipeline 1: Data Availability Check
- Verifies existence of company reports in the data lake
- Validates report accessibility and format
- Generates availability reports
- Tracks missing or inaccessible reports

### Pipeline 2: Content Extraction
- Extracts CSR indicators from PDF reports
- Processes different indicator types (reduction, increase, targets)
- Validates extracted data against predefined rules
- Generates extraction reports and logs

### Pipeline 3: Storage Implementation
- Implements scalable database solution
- Supports versioning and updates
- Maintains data integrity and validation
- Provides efficient query capabilities

### Pipeline 4: Visualization
- Interactive data exploration interface
- Customizable dashboards
- Trend analysis tools
- Data quality visualization

## Dependencies
- Python 3.13+
- Key Python packages:
  - pandas >= 2.2.3
  - PyPDF2 >= 3.0.1
  - SQLAlchemy >= 2.0.0
  - FastAPI >= 0.109.0
  - APScheduler >= 3.10.1
  - pytest >= 8.0.0

## Installation Guide and Usage Instructions
"If anyone wants to run our project locally, simply open the terminal and follow the steps below."

---
   ## *Step 1: Navigate to the Project Directory*
Before running any commands, open a terminal and navigate to the *team_Salix* directory:
⁠ bash
cd path/to/team_Salix
 ⁠

---

  ## *Step 2: Clean Up Old Docker Containers*
Before starting fresh, remove all *previous Docker containers, networks, and images*:
⁠ bash
docker stop $(docker ps -aq) 2>/dev/null
docker rm $(docker ps -aq) 2>/dev/null
docker network prune -f
docker volume prune -f
docker system prune -a -f
 ⁠

---

  ## *Step 3: Verify Docker & Poetry Installation*
Run the following commands to check if *Docker and Poetry* are installed:
⁠ bash
docker --version
poetry --version
 ⁠

---

  ## * Step 4: Start Docker Services*
Once Docker is verified, *start all required services*:
⁠ bash
docker compose up --build -d
 ⁠

---

  ## Step 5: Install Python Dependencies*
Once Docker is running, install all required *Python dependencies*:
⁠ bash
cd coursework_two
rm -rf .venv
poetry env remove --all
poetry install --no-root
 ⁠

---

## Step 6: Environment Configuration
Before running the pipelines, you need to set up your environment variables. Create a `.env` file in the root directory with the following content:

```bash
# Database Configuration
DB_HOST=localhost
DB_PORT=5439
DB_NAME=fift
DB_USER=postgres
DB_PASSWORD=postgres

# API Keys (Replace with your own keys)
XAI_API_KEY=your_xai_api_key_here
DEEPSEEK_API_KEY=your_deepseek_api_key_here

# File Paths
JSON_PATH=config/ref.json
DOWNLOAD_PATH=pipeline1/result/csr_reports
```

⚠️ **Important**: Replace the placeholder values with your actual credentials and API keys.

---

## Step 7: Execute the Pipelines in Order
The pipelines must be executed in the correct sequence. Follow these steps:

1️⃣ **Pipeline 1: Data Availability Check**
```bash
poetry run python pipeline1/modules/main.py
poetry run python pipeline1/modules/pdf_checker.py
poetry run python pipeline1/modules/process_problematic.py
```
This pipeline checks the availability of CSR reports in the data lake.

2️⃣ **Pipeline 2: Content Extraction**
```bash
poetry run python pipeline2/modules/modelv2.py
```
This pipeline extracts CSR indicators from the available reports.

3️⃣ **Pipeline 3: Storage Implementation**
```bash
poetry run python pipeline3/modules/write_to_db.py
poetry run python pipeline3/modules/write_lineage.py
```
These scripts handle database operations and data lineage tracking.

4️⃣ **Pipeline 4: Visualization**
```bash
poetry run python pipeline4/modules/dashboard.py
```
This starts the visualization dashboard.

⚠️ **Important**: Run each pipeline in sequence and wait for completion before starting the next one.

---

## Step 8: Running Tests
To ensure the system is working correctly, run the test suite:

```bash
# Make sure you're in the coursework_two directory
cd path/to/team_Salix/coursework_two

# Run all tests
poetry run pytest

# Run tests with coverage report
poetry run pytest --cov=. tests/

# Run specific pipeline tests
poetry run pytest tests/test_pipeline1/  # Test Pipeline 1
poetry run pytest tests/test_pipeline2/  # Test Pipeline 2
poetry run pytest tests/test_pipeline3/  # Test Pipeline 3
poetry run pytest tests/test_pipeline4/  # Test Pipeline 4

# Run end-to-end tests
poetry run pytest tests/test_end_to_end.py
```

The test suite includes:
- Unit tests for each pipeline
- Integration tests
- End-to-end tests
- Data validation tests

---

## Step 9: Enable Automatic Updates
To automate the process, use the scheduler:

```bash
poetry run python scheduler.py
```

This will run the pipelines according to the schedule defined in `config/scheduler_config.yaml`.

---

## Step 10: Generate and View Documentation
To generate and view the project documentation, first ensure all documentation dependencies are installed:

```bash
# Install documentation dependencies
poetry install --with docs

# Generate documentation
cd docs
poetry run make html

# View in browser
open _build/html/index.html  # On macOS
# or
xdg-open _build/html/index.html  # On Linux
```

If you encounter any errors with sphinxcontrib-mermaid, try installing it directly:
```bash
poetry run pip install sphinxcontrib-mermaid
```

The documentation includes:
- Complete API reference
- Module descriptions
- Usage examples
- Search functionality

---
