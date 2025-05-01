import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
import sys
import os
import subprocess


# Dynamically add the path to the source files
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../modules")))

from api import app

@pytest.fixture
def client():
    return TestClient(app)

@patch('api.get_connection')
def test_get_reports(mock_get_connection, client):
    # Create a mock connection and cursor
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    
    # Define what the cursor should return when fetchall is called
    mock_cursor.fetchall.return_value = [
        ('AAPL', 'Apple Inc.', 2021, 100, 200, 300, 4000),
        ('GOOGL', 'Alphabet Inc.', 2021, 150, 250, 350, 4500),
    ]
    
    # Set the mock connection to return the mock cursor
    mock_conn.cursor.return_value = mock_cursor
    mock_get_connection.return_value = mock_conn
    
    # Make a GET request to the /reports endpoint
    response = client.get('/reports')
    
    # Assert the response status code
    assert response.status_code == 200, "❌ Status code is not 200."
    print("✅ Status code is 200.")
    
    # Assert the response data
    expected_data = [
        {
            "symbol": 'AAPL',
            "company_name": 'Apple Inc.',
            "report_year": 2021,
            "scope_1": 100,
            "scope_2": 200,
            "scope_3": 300,
            "water_consumption": 4000,
        },
        {
            "symbol": 'GOOGL',
            "company_name": 'Alphabet Inc.',
            "report_year": 2021,
            "scope_1": 150,
            "scope_2": 250,
            "scope_3": 350,
            "water_consumption": 4500,
        }
    ]
    assert response.json() == expected_data, "❌ Response data does not match expected data."
    print("✅ Response data matches expected data.")
    
    # Ensure the cursor and connection are closed
    mock_cursor.close.assert_called_once()
    mock_conn.close.assert_called_once()
    print("✅ Cursor and connection closed successfully.")
def test_code_quality():
    """Run linting, formatting, and security scans for scraper.py only."""
    python_exec = sys.executable  # Get the correct Python path
    scraper_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../modules/api.py"))

    print("🔍 Running flake8 on scraper.py...")
    subprocess.run([python_exec, "-m", "flake8", scraper_path, "--max-line-length=100"], check=True)

    print("🔍 Checking code formatting with black...")
    subprocess.run([python_exec, "-m", "black", "--check", scraper_path], check=True)

    print("🔍 Sorting imports with isort...")
    subprocess.run([python_exec, "-m", "isort", "--check-only", scraper_path], check=True)

    print("🔍 Running security scans with Bandit...")
    subprocess.run([python_exec, "-m", "bandit", "-r", scraper_path], check=True)


if __name__ == "__main__":
    pytest.main(["-v", __file__])
