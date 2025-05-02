# tests/test_mongo_check.py
import pytest
from unittest.mock import patch, MagicMock
from coursework_two.modules.report_availability.CSR_availability import check_csr_report, check_report_in_mongo, get_mongo_collection

@pytest.fixture
def mock_mongo_collection():
    with patch("coursework_two.modules.report_availability.CSR_availability.get_mongo_collection") as mock:
        yield mock

def test_check_report_in_mongo_found(mock_mongo_collection):
    # Mock result found
    mock_collection = MagicMock()
    mock_collection.find_one.return_value = {"company_name": "Test Co", "report_year": "2023"}
    mock_mongo_collection.return_value = mock_collection

    result = check_report_in_mongo("Test Co", 2023)
    assert result is True


def test_check_report_in_mongo_not_found(mock_mongo_collection):
    # Mock result not found
    mock_collection = MagicMock()
    mock_collection.find_one.return_value = None
    mock_mongo_collection.return_value = mock_collection

    result = check_report_in_mongo("Unknown Co", 2023)
    assert result is False


def test_check_csr_report(mock_mongo_collection):
    # Mock result found
    mock_collection = MagicMock()
    mock_collection.find_one.return_value = {"company_name": "Sample", "report_year": "2025"}
    mock_mongo_collection.return_value = mock_collection

    result = check_csr_report("Sample", 2025)
    assert result is True