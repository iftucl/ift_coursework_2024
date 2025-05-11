import pytest
from unittest.mock import Mock, patch
from minio.error import S3Error
import hashlib
import sys, os

base = os.path.dirname(__file__)
src_dir = os.path.abspath(os.path.join(base, "..", "src"))
sys.path.insert(0, src_dir)

from team_wisteria.coursework_one.a_pipeline.src.content_extract import (
    compute_hash,
    extract,
    IndicatorDB,
    MinioReader,
    field_patterns,
    main
)

# --------------------------
# Fixtures
# --------------------------

@pytest.fixture
def sample_text():
    return '''
    Scope 1: 12,345 tCO2e
    Renewable energy share is 45.6%.
    Water withdrawal: 7,890,000
    '''

@pytest.fixture
def mock_db_conn():
    with patch("psycopg2.connect") as mock_connect:
        mock_conn = Mock()
        mock_cur = Mock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cur
        yield mock_conn, mock_cur

@pytest.fixture
def mock_minio_client():
    with patch("content_extract.Minio") as mock_minio_cls:
        mock_cli = Mock()
        mock_minio_cls.return_value = mock_cli
        yield mock_cli

# --------------------------
# Unit tests
# --------------------------

def test_compute_hash():
    text = "test content"
    expected = hashlib.md5(text.encode()).hexdigest()
    assert compute_hash(text) == expected


def test_extract_fields(sample_text):
    res = extract(sample_text, "TestCo", 2023, "dummy.txt")
    assert res["company_id"] == "TestCo"
    assert res["reporting_year"] == 2023
    assert res["scope_1_emissions"] == 12345.0
    assert res.get("renewable_energy_share") is None
    assert res["total_water_withdrawal"] == 7890000.0
    assert res.get("scope_2_emissions") is None

@pytest.mark.parametrize("text", ["No relevant data."])
def test_extract_no_matches(text):
    out = extract(text, "Co", 2020, "f.txt")
    for field in field_patterns:
        assert out[field] is None

@pytest.mark.parametrize("text", [
    "Scope 1: 1000\nScope 1: 2000\nScope 1: 1500"
])
def test_extract_multiple_without_unit(text):
    out = extract(text, "Co", 2020, "f.txt")
    assert out["scope_1_emissions"] is None

# --------------------------
# Database tests
# --------------------------

def test_indicator_db_upsert(mock_db_conn):
    mock_conn, mock_cur = mock_db_conn
    db = IndicatorDB()
    sample = {
        "company_id": "Co",
        "reporting_year": 2021,
        "source_file_path": "path",
        "__content_hash__": "h",
        "scope_1_emissions": 100.0
    }
    db.upsert(sample)
    sql_calls = [args[0] for args, _ in mock_cur.execute.call_args_list]
    assert any("INSERT INTO csr_indicators" in s for s in sql_calls)
    assert any("ON CONFLICT" in s for s in sql_calls)


def test_fetch_pdf_records(mock_db_conn):
    mock_conn, mock_cur = mock_db_conn
    mock_cur.fetchall.return_value = [("Co", 2021, "r.pdf")]
    db = IndicatorDB()
    out = db.fetch_pdf_records(["Co"])
    assert out == [("Co", 2021, "r.pdf")]

# --------------------------
# MinIOReader tests
# --------------------------

def test_minio_reader_success(mock_minio_client):
    resp = Mock()
    resp.read.return_value = b"abc"
    resp.close = Mock()
    resp.release_conn = Mock()
    mock_minio_client.get_object.return_value = resp
    reader = MinioReader()
    assert reader.get_bytes("file.txt") == b"abc"


def test_minio_reader_failure(mock_minio_client):
    mock_minio_client.get_object.side_effect = S3Error(
        "NoSuchKey", "req-id", "host-id", "resource", "Object not found", None
    )
    reader = MinioReader()
    assert reader.get_bytes("file.txt") is None

# --------------------------
# Integration test for main
# --------------------------

def test_main_flow(mock_db_conn, mock_minio_client, sample_text, capsys):
    mock_conn, mock_cur = mock_db_conn
    mock_cur.fetchall.return_value = [("TestCo", 2023, "report.pdf")]
    resp = Mock()
    resp.read.return_value = sample_text.encode('utf-8')
    resp.close = Mock()
    resp.release_conn = Mock()
    mock_minio_client.get_object.return_value = resp

    main()
    assert mock_conn.commit.call_count >= 1
    captured = capsys.readouterr()
    assert "completed" in captured.out
