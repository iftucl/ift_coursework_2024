# test_create_table.py
from modules.data_storage import create_table
from unittest.mock import MagicMock, patch

@patch("modules.data_storage.create_table.psycopg2.connect")
def test_create_tables(mock_connect):
    mock_conn = MagicMock()
    mock_connect.return_value = mock_conn
    try:
        create_table.create_table_and_insert_data()
    except Exception as e:
        assert False, f"Table creation failed: {e}"
