"""
This module provides test fixtures used by pytest for testing the `modules.data_storage` functionality.

Test Fixtures:
- `mock_db_connection`: Mocks a PostgreSQL database connection for testing purposes.
- `monkeypatch_env`: Mocks the environment variable `DEEPSEEK_API_KEY` for tests.

These fixtures help simulate interactions with external dependencies like a database and environment variables.
"""

# ※ conftest.py
# poetry run pytest test/data_storage/ --cov=modules

import pytest
from unittest.mock import MagicMock, patch

@pytest.fixture(scope="module")
def mock_db_connection():
    """
    Mocks a PostgreSQL database connection for testing.

    This fixture patches the `psycopg2.connect` function to return a fake connection and cursor.
    The cursor's `fetchall`, `fetchone`, and `execute` methods are mocked to simulate query results
    without needing an actual database connection.

    This fixture is scoped to the module, meaning it is created once per test module.

    :return: A mocked database connection.
    :rtype: MagicMock
    """
    with patch("modules.data_storage.create_table.psycopg2.connect") as mock_connect:
        # Create fake connection and fake cursor
        fake_conn = MagicMock()
        fake_cursor = MagicMock()
        
        # Set cursor() return fake_cursor
        fake_conn.cursor.return_value = fake_cursor
        fake_conn.__enter__.return_value = fake_conn
        fake_cursor.__enter__.return_value = fake_cursor  # Support with conn.cursor() as cur:

        # Set return values for mocked methods
        fake_cursor.fetchall.return_value = [("mocked", "data")]
        fake_cursor.fetchone.return_value = ("one", "row")
        fake_cursor.execute.return_value = None

        # Set connect() to return the fake connection
        mock_connect.return_value = fake_conn

        yield fake_conn

@pytest.fixture
def monkeypatch_env(monkeypatch):
    """
    Mocks the `DEEPSEEK_API_KEY` environment variable for testing.

    This fixture uses the `monkeypatch` fixture to set the environment variable `DEEPSEEK_API_KEY`
    to a mock value (`"mock-key"`) during testing. This allows tests to simulate the presence
    of the environment variable without requiring an actual key.

    :param monkeypatch: The pytest monkeypatch fixture.
    :return: None
    :rtype: None
    """
    monkeypatch.setenv("DEEPSEEK_API_KEY", "mock-key")
