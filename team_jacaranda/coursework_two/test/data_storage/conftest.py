# ※ conftest.py
# poetry run pytest test/data_storage/ --cov=modules

import pytest
from unittest.mock import MagicMock, patch

@pytest.fixture(scope="module")
def mock_db_connection():
    with patch("modules.data_storage.create_table.psycopg2.connect") as mock_connect:
        # creat fake connection and fake cursor
        fake_conn = MagicMock()
        fake_cursor = MagicMock()
        
        # set cursor() return fake_cursor
        fake_conn.cursor.return_value = fake_cursor
        fake_conn.__enter__.return_value = fake_conn
        fake_cursor.__enter__.return_value = fake_cursor  # 支持 with conn.cursor() as cur:

        # set return values
        fake_cursor.fetchall.return_value = [("mocked", "data")]
        fake_cursor.fetchone.return_value = ("one", "row")
        fake_cursor.execute.return_value = None

        # set connect() return fake connection
        mock_connect.return_value = fake_conn

        yield fake_conn

@pytest.fixture
def monkeypatch_env(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "mock-key")
