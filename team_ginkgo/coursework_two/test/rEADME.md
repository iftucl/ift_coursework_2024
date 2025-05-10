# Test Directory Overview

This directory contains various tests to ensure the correctness, reliability, and security of the project components. The tests cover unit tests, integration tests, and end-to-end tests for the data extraction, processing, storage, and retrieval functionalities.

## Test Categories

### 1. Unit Tests
Unit tests verify the functionality of individual modules:
- **`test_unit/test_scraper.py`**: Validate /reports endpoint returns correct data using mocked database connections
- **`test_unit/test_db.py`**: Verify that SQL queries are executed correctly, including the queries for creating tables and modifying table structures.
- **`test_unit/test_output.py`**: Verify download and API call logic using mocked network and file operations.

### 2. Integration Tests
Integration tests ensure that different components work together properly:
- **`test_pipeline/test_pipeline.py`**: Verify interactions between components (e.g., database connections, API calls).

### 3. End-to-End (E2E) Tests
End-to-end tests cover the entire data pipeline:
- **`test_end_to_end.py`**: Test the entire pipeline from data ingestion to storage.

## Directory Structure
```
/test
    ├── test_unit/
    │   ├── test_api.py       # Test the API endpoint of the FastAPI application
    │   ├── test_db.py      # Test database operations-related functionality
    │   ├── test_output.py         # Test functionalities related to data downloading and API calls
    ├── test_pipeline/
    │   ├── test_pipeline.py      # Integration test for data pipeline
    ├── test_end_to_end.py        # End-to-end test covering full data pipeline
```

## Running Tests
To execute the tests, use `pytest`. Ensure dependencies are installed via `poetry`:
```bash
poetry install  # Install dependencies
poetry run pytest ./tests/  # Run all tests
```

### Running Specific Tests
- Run a single test file:
  ```bash
  poetry run pytest ./tests/test_unit/test_api.py
  ```
- Run with detailed output:
  ```bash
  poetry run pytest -v
  ```
- Run tests with coverage:
  ```bash
  poetry run pytest --cov=modules ./tests/
  ```

## Code Quality Checks
The project enforces code quality standards using `flake8`, `black`, `isort`, and `bandit`:
```bash
poetry run flake8 ./modules  # Linting
poetry run black --check ./modules  # Formatting check
poetry run isort --check-only ./modules  # Import sorting check
poetry run bandit -r ./modules  # Security scan
```

## Test Coverage Target
The project aims for at least **80% test coverage** to ensure robustness.

## Conclusion
This test suite ensures the data pipeline is functional, scalable, and secure. Always run tests before committing new code to maintain stability.

