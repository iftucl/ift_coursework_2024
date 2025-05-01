import pytest
from unittest.mock import patch, MagicMock
import json
import sys
import os
import subprocess

# Dynamically add the path to the source files
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../modules")))

import output


@pytest.fixture
def mock_db_connection():
    """Fixture to mock database connection and cursor."""
    with patch('output.get_connection') as mock_get_connection:
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get_connection.return_value = mock_conn
        yield mock_conn, mock_cursor

@patch('output.requests.get')
def test_try_requests_download(mock_get):
    """Test downloading PDF using requests."""
    mock_get.return_value.status_code = 200
    mock_get.return_value.content = b'%PDF-1.4...'

    url = "http://example.com/report.pdf"
    path = os.path.join(output.DOWNLOAD_DIR, "test_report.pdf")
    
    success = output.try_requests_download(url, path)
    
    assert success, "❌ Requests download failed."
    assert os.path.exists(path), "❌ PDF file was not saved."

    print("✅ Requests download test passed.")

@patch('output.global_driver.get')
@patch('output.glob.glob')
@patch('output.shutil.move')
def test_try_selenium_download(mock_move, mock_glob, mock_get):
    """Test downloading PDF using Selenium."""
    mock_glob.return_value = [os.path.join(output.DOWNLOAD_DIR, "downloaded.pdf")]
    mock_move.return_value = None

    url = "http://example.com/report.pdf"
    path = os.path.join(output.DOWNLOAD_DIR, "test_report_selenium.pdf")

    success = output.try_selenium_download(url, path)

    assert success, "❌ Selenium download failed."
    mock_move.assert_called_once_with(mock_glob.return_value[0], path)

    print("✅ Selenium download test passed.")

@patch('output.requests.post')
def test_call_deepseek_api(mock_post):
    """Test calling DeepSeek API."""
    mock_post.return_value.status_code = 200
    mock_post.return_value.json.return_value = {
        'choices': [{'message': {'content': '{"scope_1": "100", "scope_2": "200", "scope_3": "300", "water_consumption": "400"}'}}]
    }
    
    text = "Example text content"
    response = output.call_deepseek_api(text)
    
    assert response is not None, "❌ DeepSeek API call failed."
    result = json.loads(response)
    assert result['scope_1'] == "100", "❌ Incorrect value for scope_1."
    assert result['scope_2'] == "200", "❌ Incorrect value for scope_2."
    assert result['scope_3'] == "300", "❌ Incorrect value for scope_3."
    assert result['water_consumption'] == "400", "❌ Incorrect value for water_consumption."

    print("✅ DeepSeek API call test passed.")

def test_resolve_real_symbol(mock_db_connection):
    """Test resolving real symbol from the database."""
    mock_conn, mock_cursor = mock_db_connection
    mock_cursor.fetchone.return_value = ('REAL_SYMBOL',)

    symbol = "TEST"
    year = 2020
    resolved_symbol = output.resolve_real_symbol(symbol, year)

    assert resolved_symbol == 'REAL_SYMBOL', "❌ Real symbol resolution failed."

    print("✅ Real symbol resolution test passed.")

@patch('output.get_connection')
def test_update_database(mock_get_connection):
    """Test updating the database."""
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    mock_get_connection.return_value = mock_conn

    symbol = "TEST"
    year = 2020
    scope_1 = 100.0
    scope_2 = 200.0
    scope_3 = 300.0
    water_consumption = 400.0

    output.update_database(symbol, year, scope_1, scope_2, scope_3, water_consumption)

    mock_cursor.execute.assert_called_once()
    mock_conn.commit.assert_called_once()

    print("✅ Database update test passed.")

def test_code_quality():
    """Run linting, formatting, and security scans for scraper.py only."""
    python_exec = sys.executable  # Get the correct Python path
    scraper_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../modules/output/output.py"))

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

