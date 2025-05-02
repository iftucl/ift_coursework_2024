"""
Global pytest fixtures and configuration.
"""

import os

import pandas as pd
import pytest
import yaml
from sqlalchemy import create_engine


@pytest.fixture(scope="session")
def test_config():
    """Load test configuration"""
    config_path = os.path.join("config", "test_config.yaml")
    with open(config_path, "r") as f:
        return yaml.safe_load(f)


@pytest.fixture(scope="session")
def db_engine():
    """Create test database connection"""
    DATABASE_URL = "postgresql+psycopg2://postgres:postgres@localhost:5439/fift"
    engine = create_engine(DATABASE_URL)
    yield engine
    engine.dispose()


@pytest.fixture
def sample_pdf_path():
    """Sample PDF file path for testing"""
    return os.path.join("tests", "test_data", "sample.pdf")


@pytest.fixture
def mock_esg_data():
    """Mock ESG data for testing"""
    return pd.DataFrame(
        {
            "company": ["Company A", "Company B"],
            "year": [2023, 2023],
            "scope1_emissions": [100.0, 150.0],
            "scope2_emissions": [200.0, 250.0],
            "total_energy_consumption": [1000.0, 1200.0],
            "total_water_withdrawal": [5000.0, 5500.0],
            "total_waste_generated": [300.0, 350.0],
            "employee_diversity": [45.0, 48.0],
        }
    )


@pytest.fixture
def mock_lineage_data():
    """Mock data lineage information for testing"""
    return pd.DataFrame(
        {
            "Step": [1, 2, 3],
            "Script": ["main.py", "modelv2.py", "write_to_db.py"],
            "Input": ["raw_pdf", "extracted_text", "processed_data"],
            "Processing": ["Download PDF", "Extract Text", "Write to DB"],
            "Output": ["saved_pdf", "text_data", "database_entry"],
        }
    )
