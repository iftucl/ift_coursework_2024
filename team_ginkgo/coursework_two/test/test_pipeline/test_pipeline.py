import pytest
import json
import os
from unittest.mock import patch
from db import get_connection, update_database
from output import fetch_reports_from_db, download_pdf, call_deepseek_api

@pytest.fixture(scope='module')
def db_connection():
    """Setup database connection for integration tests."""
    conn = get_connection()
    yield conn
    conn.close()

def test_database_connection(db_connection):
    """Verify database connection is established."""
    assert db_connection is not None, "❌ Database connection failed."
    cursor = db_connection.cursor()
    cursor.execute("SELECT 1;")
    result = cursor.fetchone()
    assert result[0] == 1, "⚠️ Database query failed."
    cursor.close()

def test_fetch_reports_from_db(db_connection):
    """Test fetching reports from the database."""
    rows = fetch_reports_from_db()
    assert isinstance(rows, list), "❌ Fetch reports did not return a list."
    assert len(rows) > 0, "⚠️ No reports fetched from the database."

def test_download_pdf():
    """Test downloading PDF from a given URL."""
    symbol = "TEST"
    url = "http://example.com/test.pdf"
    year = 2025
    save_path = download_pdf(url, symbol, year)
    assert save_path is not None, "❌ PDF download failed."
    assert os.path.exists(save_path), "⚠️ Downloaded PDF file does not exist."
    # Cleanup downloaded file
    os.remove(save_path)

@patch('output.call_deepseek_api')
def test_call_deepseek_api(mock_call_deepseek_api):
    """Test calling DeepSeek API."""
    mock_response = json.dumps({
        'scope_1': 100.0,
        'scope_2': 200.0,
        'scope_3': 300.0,
        'water_consumption': 400.0
    })
    mock_call_deepseek_api.return_value = mock_response

    pdf_content = b"%PDF-1.4 test content"
    response = call_deepseek_api(pdf_content)
    assert response == mock_response, "⚠️ API call returned unexpected response."

def test_update_database(db_connection):
    """Test updating the database with new data."""
    symbol = "TEST"
    year = 2025
    scope_1 = 100.0
    scope_2 = 200.0
    scope_3 = 300.0
    water_consumption = 400.0

    update_database(symbol, year, scope_1, scope_2, scope_3, water_consumption)

    cursor = db_connection.cursor()
    cursor.execute("""
        SELECT scope_1, scope_2, scope_3, water_consumption
        FROM ginkgo.csr_reports_with_indicators
        WHERE symbol = %s AND report_year = %s;
    """, (symbol, year))
    result = cursor.fetchone()
    cursor.close()

    assert result is not None, "❌ Data not found in database."
    assert result[0] == scope_1, "⚠️ Incorrect scope_1 value in database."
    assert result[1] == scope_2, "⚠️ Incorrect scope_2 value in database."
    assert result[2] == scope_3, "⚠️ Incorrect scope_3 value in database."
    assert result[3] == water_consumption, "⚠️ Incorrect water_consumption value in database."

if __name__ == "__main__":
    pytest.main()
