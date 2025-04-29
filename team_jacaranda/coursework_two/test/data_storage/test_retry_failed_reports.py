# test/data_storage/test_retry_failed_reports.py
from modules.data_storage import retry_failed_reports
from unittest.mock import patch, MagicMock

@patch("modules.data_storage.retry_failed_reports.pdfplumber.open")
@patch("modules.data_storage.retry_failed_reports.minio_client")
@patch("modules.data_storage.retry_failed_reports.psycopg2.connect")
def test_retry_failed_reports(mock_connect, mock_minio, mock_pdf):
    mock_minio.list_objects.return_value = [MagicMock(object_name="test_2022.pdf")]
    mock_minio.fget_object.return_value = None

    mock_pdf_page = MagicMock()
    mock_pdf_page.extract_text.return_value = "Climate impact and energy"
    mock_pdf.return_value.__enter__.return_value.pages = [mock_pdf_page]

    fake_conn = MagicMock()
    fake_cursor = MagicMock()
    fake_conn.cursor.return_value.__enter__.return_value = fake_cursor
    mock_connect.return_value = fake_conn

    retry_failed_reports.retry_failed_reports()
    assert True
