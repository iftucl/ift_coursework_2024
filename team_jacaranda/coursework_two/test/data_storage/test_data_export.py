from modules.data_storage import data_export
from unittest.mock import MagicMock, patch
import os

@patch("modules.data_storage.data_export.psycopg2.connect")
def test_export_table_to_csv(mock_connect):
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.fetchall.return_value = [(1, "test")]
    mock_cursor.description = [("id",), ("name",)]
    mock_conn.cursor.return_value = mock_cursor
    mock_connect.return_value = mock_conn

    output_path = os.path.join("/tmp", "csr_indicators.csv")
    data_export.export_table_to_csv("csr_reporting.csr_indicators", output_path, mock_conn)
    assert os.path.exists(output_path)
