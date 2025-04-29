# test/data_storage/test_retry_failed_reports.py
import json
import builtins
from unittest.mock import patch, MagicMock, mock_open
from pathlib import Path
import pytest

from modules.data_storage import retry_failed_reports


# === Case 1: JSON 不存在 ===
@patch("modules.data_storage.retry_failed_reports.Path.exists", return_value=False)
def test_no_failed_json(mock_exists):
    retry_failed_reports.retry_failed_reports()  # 应该直接 return，不报错
    assert True


# === Case 2: JSON 为空列表 ===
@patch("modules.data_storage.retry_failed_reports.Path.exists", return_value=True)
@patch("builtins.open", new_callable=mock_open, read_data='[]')
def test_empty_failed_json(mock_open_file, mock_exists):
    retry_failed_reports.retry_failed_reports()
    assert True


# === Case 3: parse_security_and_year 返回 None（无效文件名）===
@patch("modules.data_storage.retry_failed_reports.Path.exists", return_value=True)
@patch("builtins.open", new_callable=mock_open, read_data='["invalidfile.pdf"]')
@patch("modules.data_storage.retry_failed_reports.psycopg2.connect")
def test_invalid_filename_skipped(mock_connect, mock_open_file, mock_exists):
    conn = MagicMock()
    cur = MagicMock()
    conn.cursor.return_value.__enter__.return_value = cur
    mock_connect.return_value = conn
    cur.fetchall.return_value = []
    retry_failed_reports.retry_failed_reports()
    assert True


# === Case 4: 下载失败 ===
@patch("modules.data_storage.retry_failed_reports.Path.exists", return_value=True)
@patch("builtins.open", new_callable=mock_open, read_data='["test_2022.pdf"]')
@patch("modules.data_storage.retry_failed_reports.minio_client.fget_object", side_effect=Exception("Download error"))
@patch("modules.data_storage.retry_failed_reports.psycopg2.connect")
def test_download_error(mock_connect, mock_fget, mock_open_file, mock_exists):
    conn = MagicMock()
    cur = MagicMock()
    conn.cursor.return_value.__enter__.return_value = cur
    mock_connect.return_value = conn
    cur.fetchall.return_value = [(1, "Energy", ["energy", "emission"])]
    retry_failed_reports.retry_failed_reports()
    assert True


# === Case 5: 匹配失败（无段落命中）===
@patch("modules.data_storage.retry_failed_reports.Path.exists", return_value=True)
@patch("builtins.open", new_callable=mock_open, read_data='["test_2022.pdf"]')
@patch("modules.data_storage.retry_failed_reports.minio_client.fget_object", return_value=None)
@patch("modules.data_storage.retry_failed_reports.psycopg2.connect")
@patch("modules.data_storage.retry_failed_reports.pdfplumber.open")
def test_no_matching_paragraphs(mock_pdf, mock_connect, mock_fget, mock_open_file, mock_exists):
    page = MagicMock()
    page.extract_text.return_value = "This is something else unrelated."
    mock_pdf.return_value.__enter__.return_value.pages = [page]

    conn = MagicMock()
    cur = MagicMock()
    conn.cursor.return_value.__enter__.return_value = cur
    cur.fetchall.return_value = [(1, "Energy", ["energy", "climate"])]
    mock_connect.return_value = conn

    retry_failed_reports.retry_failed_reports()
    assert True


# === Case 6: 匹配成功 ===
@patch("modules.data_storage.retry_failed_reports.Path.exists", return_value=True)
@patch("builtins.open", new_callable=mock_open, read_data='["test_2022.pdf"]')
@patch("modules.data_storage.retry_failed_reports.minio_client.fget_object", return_value=None)
@patch("modules.data_storage.retry_failed_reports.psycopg2.connect")
@patch("modules.data_storage.retry_failed_reports.pdfplumber.open")
@patch("os.path.exists", return_value=True)
@patch("os.remove")
def test_successful_extraction(mock_remove, mock_os_exists, mock_pdf, mock_connect, mock_fget, mock_open_file, mock_exists):
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


# === Case 7: PDF 文本提取返回 None ===
@patch("modules.data_storage.retry_failed_reports.Path.exists", return_value=True)
@patch("builtins.open", new_callable=mock_open, read_data='["test_2022.pdf"]')
@patch("modules.data_storage.retry_failed_reports.minio_client.fget_object", return_value=None)
@patch("modules.data_storage.retry_failed_reports.psycopg2.connect")
@patch("modules.data_storage.retry_failed_reports.pdfplumber.open")
def test_pdf_page_no_text(mock_pdf, mock_connect, mock_fget, mock_open_file, mock_exists):
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


# === Case 8: 所有文件成功处理，failed_reports.json 被删除 ===
@patch("modules.data_storage.retry_failed_reports.Path.exists", return_value=True)
@patch("builtins.open", new_callable=mock_open, read_data='["test_2022.pdf"]')
@patch("modules.data_storage.retry_failed_reports.minio_client.fget_object", return_value=None)
@patch("modules.data_storage.retry_failed_reports.psycopg2.connect")
@patch("modules.data_storage.retry_failed_reports.pdfplumber.open")
@patch("os.path.exists", return_value=True)
@patch("os.remove")
@patch("modules.data_storage.retry_failed_reports.Path.unlink")
def test_failed_json_removed_after_success(mock_unlink, mock_remove, mock_os_exists, mock_pdf, mock_connect, mock_fget, mock_open_file, mock_exists):
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
