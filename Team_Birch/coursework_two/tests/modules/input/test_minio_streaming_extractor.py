import logging
from unittest.mock import MagicMock, patch

import pytest
from minio.error import S3Error

# Module to test
from modules.input.minio_streaming_extractor import (
    connect_to_minio_from_env,
    stream_pdf_and_extract,
)


@pytest.fixture
def mock_minio_client():
    """Fixture providing a mocked MinIO client"""
    client = MagicMock()
    mock_object = MagicMock()
    mock_object.object_name = "test_company_2022.pdf"
    mock_object.bucket_name = "test-bucket"
    client.list_objects.return_value = [mock_object]
    return client


@pytest.fixture
def mock_pdf_content():
    """Fixture providing dummy PDF content"""
    return b"%PDF-1.4 fake PDF content"


def test_connect_to_minio_from_env(monkeypatch):
    """Test MinIO connection with environment variables"""
    monkeypatch.setenv("MINIO_ENDPOINT", "localhost:9000")
    monkeypatch.setenv("MINIO_ACCESS_KEY", "testkey")
    monkeypatch.setenv("MINIO_SECRET_KEY", "testsecret")
    monkeypatch.setenv("MINIO_SECURE", "false")

    client = connect_to_minio_from_env()
    assert client is not None
    # Verify by checking if it has essential methods
    assert hasattr(client, "get_object")
    assert hasattr(client, "list_objects")


@patch("modules.input.minio_streaming_extractor.extract_indicators_from_bytes")
def test_stream_pdf_and_extract_success(
    mock_extract, mock_minio_client, mock_pdf_content, tmp_path
):
    """Test that PDF streaming initiates extraction"""
    # Minimal setup
    mock_object = MagicMock(object_name="test.pdf")
    mock_minio_client.list_objects.return_value = [mock_object]
    mock_minio_client.get_object.return_value = MagicMock(
        read=MagicMock(return_value=b"%PDF-1.4")
    )

    # Create dummy files
    (tmp_path / "indicators.yaml").write_text("")
    output_csv = tmp_path / "output.csv"
    log_path = tmp_path / "extraction.log"

    # Execute
    stream_pdf_and_extract(
        minio_client=mock_minio_client,
        bucket="test-bucket",
        config_path=tmp_path / "indicators.yaml",
        output_csv=output_csv,
        log_path=log_path,
    )

    # Simplified verification
    assert mock_extract.called  # Just verify the function was called


@patch("modules.input.minio_streaming_extractor.extract_indicators_from_bytes")
def test_stream_pdf_non_pdf_skipped(mock_extract, mock_minio_client, tmp_path):
    """Test that non-PDF files are skipped"""
    mock_object = MagicMock()
    mock_object.object_name = "not_a_pdf.txt"
    mock_minio_client.list_objects.return_value = [mock_object]

    # Create real config file
    config_path = tmp_path / "config.yaml"
    config_path.write_text("dummy content")

    stream_pdf_and_extract(
        minio_client=mock_minio_client,
        bucket="test-bucket",
        config_path=config_path,
        output_csv=tmp_path / "output.csv",
        log_path=tmp_path / "log.txt",
    )

    mock_extract.assert_not_called()


@patch("modules.input.minio_streaming_extractor.extract_indicators_from_bytes")
def test_stream_pdf_handles_s3_error(mock_extract, mock_minio_client, tmp_path, caplog):
    """Test S3 error handling during PDF download"""
    # Create real config file
    config_path = tmp_path / "config.yaml"
    config_path.write_text("dummy content")

    mock_minio_client.get_object.side_effect = S3Error(
        code="NoSuchKey",
        message="Object not found",
        resource="/test-bucket/missing.pdf",
        request_id="test",
        host_id="test",
        response="test",
    )

    with caplog.at_level(logging.ERROR):
        stream_pdf_and_extract(
            minio_client=mock_minio_client,
            bucket="test-bucket",
            config_path=config_path,
            output_csv=tmp_path / "output.csv",
            log_path=tmp_path / "log.txt",
        )

    assert "Failed to process" in caplog.text


@patch("modules.input.minio_streaming_extractor.extract_indicators_from_bytes")
def test_stream_pdf_handles_extraction_error(
    mock_extract, mock_minio_client, mock_pdf_content, tmp_path, caplog
):
    """Test error handling during indicator extraction"""
    # Create real config file
    config_path = tmp_path / "config.yaml"
    config_path.write_text("dummy content")

    mock_response = MagicMock()
    mock_response.read.return_value = mock_pdf_content
    mock_minio_client.get_object.return_value = mock_response
    mock_extract.side_effect = Exception("Extraction failed")

    with caplog.at_level(logging.ERROR):
        stream_pdf_and_extract(
            minio_client=mock_minio_client,
            bucket="test-bucket",
            config_path=config_path,
            output_csv=tmp_path / "output.csv",
            log_path=tmp_path / "log.txt",
        )

    assert "Failed to process" in caplog.text


def test_config_file_not_found(mock_minio_client, tmp_path):
    """Test handling of missing config file"""
    with pytest.raises(FileNotFoundError):
        stream_pdf_and_extract(
            minio_client=mock_minio_client,
            bucket="test-bucket",
            config_path=tmp_path / "missing.yaml",
            output_csv=tmp_path / "output.csv",
            log_path=tmp_path / "log.txt",
        )
