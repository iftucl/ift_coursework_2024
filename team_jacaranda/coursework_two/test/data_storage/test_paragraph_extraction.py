# test/data_storage/test_paragraph_extraction.py
import pytest
from unittest.mock import MagicMock, patch
import json
import os
import datetime
import psycopg2
from io import BytesIO
from pathlib import Path
from tqdm import tqdm
from modules.data_storage import paragraph_extraction
from fuzzywuzzy import fuzz

# === Mock data ===
mock_indicators = [
    (1, "Renewable Energy", ["solar", "renewable", "energy"]),
    (2, "Water Usage", ["water", "usage", "conservation"])
]

mock_paragraphs = [
    (1, "This paragraph talks about solar energy and its impact."),
    (2, "This paragraph discusses water usage and its conservation efforts."),
    (3, "This is a generic paragraph with no match.")
]

# === Mock MinIO ===
@pytest.fixture
def mock_minio():
    with patch.object(paragraph_extraction.minio_client, 'fget_object', return_value=None) as mock_fget:
        yield mock_fget

# === Mock Database ===
@pytest.fixture
def mock_db():
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    yield mock_conn

# === Test extract_paragraphs_from_pdf ===
def test_extract_paragraphs_from_pdf(mock_minio):
    test_pdf = BytesIO(b"%PDF-1.4\n1 0 obj\n<< /Type /Page >>\nendobj\n")
    with patch("pdfplumber.open", return_value=MagicMock(pages=[MagicMock(extract_text=lambda: "This is a test paragraph.")])):
        paragraphs = list(paragraph_extraction.extract_paragraphs_from_pdf(test_pdf))
        assert len(paragraphs) > 0
        assert paragraphs[0][1] == "This is a test paragraph."

# === Test find_matching_paragraphs ===
def test_find_matching_paragraphs():
    result = paragraph_extraction.find_matching_paragraphs(mock_paragraphs, ["solar", "energy"])
    assert len(result) == 1
    assert result[0]['text'] == "This paragraph talks about solar energy and its impact."

    result_no_match = paragraph_extraction.find_matching_paragraphs(mock_paragraphs, ["nonexistent", "keyword"])
    assert len(result_no_match) == 0

# === Test insert_matched_data ===
@patch("psycopg2.connect")
def test_insert_matched_data(mock_db, mock_minio):
    mock_cursor = mock_db.cursor.return_value.__enter__.return_value
    mock_cursor.fetchone.return_value = [123]  # Simulate returning a data_id

    matched_data = [{"page": 1, "text": "This is a matched paragraph."}]
    extraction_time = datetime.datetime.now()

    paragraph_extraction.insert_matched_data(
        mock_db, "AAPL", 2023, 1, "Renewable Energy", matched_data, extraction_time
    )

    mock_cursor.execute.assert_called_once()
    args, kwargs = mock_cursor.execute.call_args
    assert "INSERT INTO csr_reporting.CSR_Data" in args[0]
    assert json.dumps(matched_data) in args[0]
    assert extraction_time in args[0]

# === Test check_memory_usage ===
def test_check_memory_usage():
    with patch("psutil.virtual_memory", return_value=MagicMock(percent=85)):
        result = paragraph_extraction.check_memory_usage(90)
        assert result is True

    with patch("psutil.virtual_memory", return_value=MagicMock(percent=95)):
        result = paragraph_extraction.check_memory_usage(90)
        assert result is False

# === Test process_report ===
@patch("psycopg2.connect")
@patch("modules.data_storage.paragraph_extraction.minio_client.fget_object")
def test_process_report(mock_fget, mock_db):
    mock_fget.return_value = None
    mock_cursor = mock_db.cursor.return_value.__enter__.return_value
    mock_cursor.fetchone.return_value = [123]  # Simulate returning a data_id

    result = paragraph_extraction.process_report((mock_db, MagicMock(object_name="AAPL_2023.pdf"), mock_indicators))
    assert result is None  # If no exception occurs, the result should be None
    mock_cursor.execute.assert_called()

# === Test process_all_pdfs ===
@patch("psycopg2.connect")
@patch("modules.data_storage.paragraph_extraction.minio_client.list_objects")
@patch("modules.data_storage.paragraph_extraction.minio_client.fget_object")
def test_process_all_pdfs(mock_fget, mock_list_objects, mock_db):
    mock_list_objects.return_value = [MagicMock(object_name="AAPL_2023.pdf"), MagicMock(object_name="GOOG_2023.pdf")]
    mock_fget.return_value = None
    mock_cursor = mock_db.cursor.return_value.__enter__.return_value
    mock_cursor.fetchone.return_value = [123]  # Simulate returning a data_id

    paragraph_extraction.process_all_pdfs()

    mock_list_objects.assert_called_once_with(paragraph_extraction.MINIO_BUCKET, recursive=True)
    assert mock_fget.call_count == 2
    assert mock_cursor.execute.call_count > 0

# === Test parsing of security and year ===
def test_parse_security_and_year():
    result = paragraph_extraction.parse_security_and_year("AAPL_2023.pdf")
    assert result == ("AAPL", 2023)

    result_invalid = paragraph_extraction.parse_security_and_year("invalid_file.pdf")
    assert result_invalid == (None, None)

# === Test memory management ===
def test_memory_management():
    # Simulate high memory usage
    with patch("psutil.virtual_memory", return_value=MagicMock(percent=95)):
        assert paragraph_extraction.check_memory_usage(90) is False

    # Simulate low memory usage
    with patch("psutil.virtual_memory", return_value=MagicMock(percent=80)):
        assert paragraph_extraction.check_memory_usage(90) is True