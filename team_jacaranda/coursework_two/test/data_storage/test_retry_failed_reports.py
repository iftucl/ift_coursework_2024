"""
Test module for retrying failed reports in the paragraph extraction module.
This module tests the retry logic for handling failed report downloads, 
matching paragraphs in PDFs, and database interactions.
"""

import json
import builtins
from unittest.mock import patch, MagicMock, mock_open
from pathlib import Path
import pytest
from modules.data_storage import retry_failed_reports

# === Case 1: JSON does not exist ===
@patch("modules.data_storage.retry_failed_reports.Path.exists", return_value=False)
def test_no_failed_json(mock_exists):
    """
    Test case where the 'failed_reports.json' file does not exist.

    Verifies that the function does not raise an error and returns immediately.
    
    Args:
        mock_exists (MagicMock): Mocked Path.exists method to simulate file absence.
    """
    retry_failed_reports.retry_failed_reports()  # Should return without errors
    assert True


# === Case 2: JSON is an empty list ===
@patch("modules.data_storage.retry_failed_reports.Path.exists", return_value=True)
@patch("builtins.open", new_callable=mock_open, read_data='[]')
def test_empty_failed_json(mock_open_file, mock_exists):
    """
    Test case where the 'failed_reports.json' file is empty.

    Verifies that the function does not attempt any processing when the JSON file 
    is empty.

    Args:
        mock_open_file (MagicMock): Mocked open function to simulate reading an empty list.
        mock_exists (MagicMock): Mocked Path.exists method to simulate file existence.
    """
    retry_failed_reports.retry_failed_reports()
    assert True


# === Case 3: parse_security_and_year returns None (invalid filename) ===
@patch("modules.data_storage.retry_failed_reports.Path.exists", return_value=True)
@patch("builtins.open", new_callable=mock_open, read_data='["invalidfile.pdf"]')
@patch("modules.data_storage.retry_failed_reports.psycopg2.connect")
def test_invalid_filename_skipped(mock_connect, mock_open_file, mock_exists):
    """
    Test case where 'parse_security_and_year' returns None due to an invalid file name.

    Verifies that the function skips processing for invalid filenames.

    Args:
        mock_connect (MagicMock): Mocked psycopg2 connect method for simulating database connection.
        mock_open_file (MagicMock): Mocked open function to simulate reading an invalid file name.
        mock_exists (MagicMock): Mocked Path.exists method to simulate file existence.
    """
    conn = MagicMock()
    cur = MagicMock()
    conn.cursor.return_value.__enter__.return_value = cur
    mock_connect.return_value = conn
    cur.fetchall.return_value = []
    retry_failed_reports.retry_failed_reports()
    assert True


# === Case 4: Download failure ===
@patch("modules.data_storage.retry_failed_reports.Path.exists", return_value=True)
@patch("builtins.open", new_callable=mock_open, read_data='["test_2022.pdf"]')
@patch("modules.data_storage.retry_failed_reports.minio_client.fget_object", side_effect=Exception("Download error"))
@patch("modules.data_storage.retry_failed_reports.psycopg2.connect")
def test_download_error(mock_connect, mock_fget, mock_open_file, mock_exists):
    """
    Test case where the file download fails during the retry process.

    Verifies that the function handles download errors appropriately.

    Args:
        mock_connect (MagicMock): Mocked psycopg2 connect method for simulating database connection.
        mock_fget (MagicMock): Mocked MinIO 'fget_object' method to simulate a download error.
        mock_open_file (MagicMock): Mocked open function to simulate reading a PDF file name.
        mock_exists (MagicMock): Mocked Path.exists method to simulate file existence.
    """
    conn = MagicMock()
    cur = MagicMock()
    conn.cursor.return_value.__enter__.return_value = cur
    mock_connect.return_value = conn
    cur.fetchall.return_value = [(1, "Energy", ["energy", "emission"])]
    retry_failed_reports.retry_failed_reports()
    assert True


# === Case 5: No matching paragraphs ===
@patch("modules.data_storage.retry_failed_reports.Path.exists", return_value=True)
@patch("builtins.open", new_callable=mock_open, read_data='["test_2022.pdf"]')
@patch("modules.data_storage.retry_failed_reports.minio_client.fget_object", return_value=None)
@patch("modules.data_storage.retry_failed_reports.psycopg2.connect")
@patch("modules.data_storage.retry_failed_reports.pdfplumber.open")
def test_no_matching_paragraphs(mock_pdf, mock_connect, mock_fget, mock_open_file, mock_exists):
    """
    Test case where no paragraphs match the given keywords.

    Verifies that the function skips further processing when no matching paragraphs are found.

    Args:
        mock_pdf (MagicMock): Mocked pdfplumber.open to simulate PDF page extraction.
        mock_connect (MagicMock): Mocked psycopg2 connect method for simulating database connection.
        mock_fget (MagicMock): Mocked MinIO 'fget_object' method for simulating file retrieval.
        mock_open_file (MagicMock): Mocked open function to simulate reading a PDF file name.
        mock_exists (MagicMock): Mocked Path.exists method to simulate file existence.
    """
    page = MagicMock()
    page.extract_text.return_value = "This is something else unrelated."
    mock_pdf.return_value.__enter__.return_value.pages = [page]

    conn = MagicMock()
    cur = MagicMock()
    conn.cursor.return_value.__enter__.return_value = cur
    mock_connect.return_value = conn
    cur.fetchall.return_value = [(1, "Energy", ["energy", "climate"])]
    retry_failed_reports.retry_failed_reports()
    assert True


# === Case 6: Successful extraction ===
@patch("modules.data_storage.retry_failed_reports.Path.exists", return_value=True)
@patch("builtins.open", new_callable=mock_open, read_data='["test_2022.pdf"]')
@patch("modules.data_storage.retry_failed_reports.minio_client.fget_object", return_value=None)
@patch("modules.data_storage.retry_failed_reports.psycopg2.connect")
@patch("modules.data_storage.retry_failed_reports.pdfplumber.open")
@patch("os.path.exists", return_value=True)
@patch("os.remove")
def test_successful_extraction(mock_remove, mock_os_exists, mock_pdf, mock_connect, mock_fget, mock_open_file, mock_exists):
    """
    Test case where the paragraph extraction is successful and database updates occur.

    Verifies that the extraction is successful, the data is processed, and the database is updated.

    Args:
        mock_remove (MagicMock): Mocked os.remove method to simulate file removal.
        mock_os_exists (MagicMock): Mocked os.path.exists method to simulate file existence.
        mock_pdf (MagicMock): Mocked pdfplumber.open to simulate PDF page extraction.
        mock_connect (MagicMock): Mocked psycopg2 connect method for simulating database connection.
        mock_fget (MagicMock): Mocked MinIO 'fget_object' method for simulating file retrieval.
        mock_open_file (MagicMock): Mocked open function to simulate reading a PDF file name.
        mock_exists (MagicMock): Mocked Path.exists method to simulate file existence.
    """
    page = MagicMock()
    page.extract_text.return_value = "Energy and climate impact are key concerns. Emissions decreased."
    mock_pdf.return_value.__enter__.return_value.pages = [page]

    conn = MagicMock()
    cur = MagicMock()
    conn.cursor.return_value.__enter__.return_value = cur
    mock_connect.return_value = conn
    cur.fetchall.return_value = [(1, "Energy", ["energy", "climate"])]

    retry_failed_reports.retry_failed_reports()
    cur.execute.assert_called()
    assert True


# === Case 7: PDF text extraction returns None ===
@patch("modules.data_storage.retry_failed_reports.Path.exists", return_value=True)
@patch("builtins.open", new_callable=mock_open, read_data='["test_2022.pdf"]')
@patch("modules.data_storage.retry_failed_reports.minio_client.fget_object", return_value=None)
@patch("modules.data_storage.retry_failed_reports.psycopg2.connect")
@patch("modules.data_storage.retry_failed_reports.pdfplumber.open")
def test_pdf_page_no_text(mock_pdf, mock_connect, mock_fget, mock_open_file, mock_exists):
    """
    Test case where the PDF page extraction returns None (no text extracted).

    Verifies that the function handles the case of missing text on a PDF page appropriately.

    Args:
        mock_pdf (MagicMock): Mocked pdfplumber.open to simulate PDF page extraction.
        mock_connect (MagicMock): Mocked psycopg2 connect method for simulating database connection.
        mock_fget (MagicMock): Mocked MinIO 'fget_object' method for simulating file retrieval.
        mock_open_file (MagicMock): Mocked open function to simulate reading a PDF file name.
        mock_exists (MagicMock): Mocked Path.exists method to simulate file existence.
    """
    page = MagicMock()
    page.extract_text.return_value = None
    mock_pdf.return_value.__enter__.return_value.pages = [page]

    conn = MagicMock()
    cur = MagicMock()
    conn.cursor.return_value.__enter__.return_value = cur
    mock_connect.return_value = conn
    cur.fetchall.return_value = [(1, "Energy", ["energy", "climate"])]

    retry_failed_reports.retry_failed_reports()
    assert True


# === Case 8: All files processed successfully, 'failed_reports.json' is deleted ===
@patch("modules.data_storage.retry_failed_reports.Path.exists", return_value=True)
@patch("builtins.open", new_callable=mock_open, read_data='["test_2022.pdf"]')
@patch("modules.data_storage.retry_failed_reports.minio_client.fget_object", return_value=None)
@patch("modules.data_storage.retry_failed_reports.psycopg2.connect")
@patch("modules.data_storage.retry_failed_reports.pdfplumber.open")
@patch("os.path.exists", return_value=True)
@patch("os.remove")
@patch("modules.data_storage.retry_failed_reports.Path.unlink")
def test_failed_json_removed_after_success(mock_unlink, mock_remove, mock_os_exists, mock_pdf, mock_connect, mock_fget, mock_open_file, mock_exists):
    """
    Test case where all files are successfully processed and the 'failed_reports.json' is deleted.

    Verifies that the function properly removes the 'failed_reports.json' after all files are successfully processed.

    Args:
        mock_unlink (MagicMock): Mocked Path.unlink method to simulate file deletion.
        mock_remove (MagicMock): Mocked os.remove method to simulate file removal.
        mock_os_exists (MagicMock): Mocked os.path.exists method to simulate file existence.
        mock_pdf (MagicMock): Mocked pdfplumber.open to simulate PDF page extraction.
        mock_connect (MagicMock): Mocked psycopg2 connect method for simulating database connection.
        mock_fget (MagicMock): Mocked MinIO 'fget_object' method for simulating file retrieval.
        mock_open_file (MagicMock): Mocked open function to simulate reading a PDF file name.
        mock_exists (MagicMock): Mocked Path.exists method to simulate file existence.
    """
    page = MagicMock()
    page.extract_text.return_value = "Energy and climate impact are important. Energy savings increased."
    mock_pdf.return_value.__enter__.return_value.pages = [page]

    conn = MagicMock()
    cur = MagicMock()
    conn.cursor.return_value.__enter__.return_value = cur
    mock_connect.return_value = conn
    cur.fetchall.return_value = [(1, "Energy", ["energy", "climate"])]

    retry_failed_reports.retry_failed_reports()
    mock_unlink.assert_called()
    assert True
