import pytest
import psycopg2
from unittest.mock import patch, MagicMock
import sys
import os
import subprocess

# Dynamically add the path to the source files
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../modules")))

from db import create_reports_with_indicators

@pytest.fixture
def mock_db_connection():
    """Fixture to mock database connection and cursor."""
    with patch('db.get_connection') as mock_get_connection:
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get_connection.return_value = mock_conn
        yield mock_conn, mock_cursor

def test_create_reports_with_indicators(mock_db_connection):
    """Test the creation and modification of csr_reports_with_indicators table."""
    mock_conn, mock_cursor = mock_db_connection

    print("\n🔍 Testing create_reports_with_indicators...")
    create_reports_with_indicators()
    
    executed_sql = [call_args[0][0] for call_args in mock_cursor.execute.call_args_list]

    assert any("CREATE TABLE IF NOT EXISTS ginkgo.csr_reports_with_indicators" in sql for sql in executed_sql)
    assert any("ALTER TABLE ginkgo.csr_reports_with_indicators" in sql for sql in executed_sql)
    assert any("UPDATE ginkgo.csr_reports_with_indicators" in sql for sql in executed_sql)
    print("✅ All expected SQL fragments found in calls.")

    # Ensure commit is called after each operation
    assert mock_conn.commit.call_count == 3, "❌ Commits not called correctly."
    print("✅ Commits executed correctly.")

    # Ensure the cursor and connection are closed
    mock_cursor.close.assert_called_once()
    mock_conn.close.assert_called_once()
    print("✅ Connection and cursor closed.")

def test_code_quality():
    """Run linting, formatting, and security scans for scraper.py only."""
    python_exec = sys.executable  # Get the correct Python path
    scraper_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../modules/db.py"))

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

