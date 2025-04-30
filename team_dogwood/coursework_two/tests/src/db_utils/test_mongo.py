import os
import sys
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime

sys.path.append(os.path.join(os.path.dirname(__file__), "../../.."))

from src.db_utils.mongo import MongCollection

# Dummy models to avoid import issues
class DummyCompany:
    def __init__(self, symbol="AAPL", security="Apple Inc."):
        self.symbol = symbol
        self.security = security
    def model_dump(self, exclude=None):
        return {"symbol": self.symbol, "security": self.security}

class DummyESGReport:
    def __init__(self, url="http://example.com", year=2023):
        self.url = url
        self.year = year
    def model_dump(self):
        return {"url": self.url, "year": self.year}

class DummyDocument:
    def __init__(self, content="test"):
        self.content = content
    def model_dump(self):
        return {"content": self.content}

def mock_mongo_hierarchy():
    """Helper to create a mock MongoClient -> db -> collection chain."""
    mock_client = MagicMock()
    mock_db = MagicMock()
    mock_collection = MagicMock()
    mock_client.__getitem__.return_value = mock_db
    mock_db.__getitem__.return_value = mock_collection
    return mock_client, mock_db, mock_collection

@patch("src.db_utils.mongo.MongoClient")
def test_insert_report_success(mock_mongo):
    mock_client, mock_db, mock_collection = mock_mongo_hierarchy()
    mock_mongo.return_value = mock_client

    company = DummyCompany()
    report_metadata = DummyESGReport()
    report = [DummyDocument("page1"), DummyDocument("page2")]

    db = MongCollection()
    db.insert_report(company, report_metadata, report)

    assert mock_collection.insert_one.called
    args, kwargs = mock_collection.insert_one.call_args
    assert args[0]["company"]["security"] == "Apple Inc."
    assert args[0]["report_metadata"]["year"] == 2023
    assert isinstance(args[0]["text_extraction_timestamp"], datetime)
    assert args[0]["report"][0]["content"] == "page1"

@patch("src.db_utils.mongo.MongoClient")
def test_insert_report_exception(mock_mongo):
    mock_client, mock_db, mock_collection = mock_mongo_hierarchy()
    mock_collection.insert_one.side_effect = Exception("fail")
    mock_mongo.return_value = mock_client

    company = DummyCompany()
    report_metadata = DummyESGReport()
    report = [DummyDocument("page1")]

    db = MongCollection()
    db.insert_report(company, report_metadata, report)

@patch("src.db_utils.mongo.MongoClient")
def test_get_report_by_company_found(mock_mongo):
    mock_client, mock_db, mock_collection = mock_mongo_hierarchy()
    mock_collection.find_one.return_value = {
        "report": [{"content": "page1"}, {"content": "page2"}]
    }
    mock_mongo.return_value = mock_client

    company = DummyCompany()
    db = MongCollection()

    # Patch Document to DummyDocument
    with patch("src.db_utils.mongo.Document", DummyDocument):
        result = db.get_report_by_company(company)
        assert isinstance(result, list)
        assert result[0].content == "page1"

@patch("src.db_utils.mongo.MongoClient")
def test_get_report_by_company_not_found(mock_mongo):
    mock_client, mock_db, mock_collection = mock_mongo_hierarchy()
    mock_collection.find_one.return_value = None
    mock_mongo.return_value = mock_client

    company = DummyCompany()
    db = MongCollection()
    with patch("src.db_utils.mongo.Document", DummyDocument):
        result = db.get_report_by_company(company)
        assert result is None

@patch("src.db_utils.mongo.MongoClient")
def test_get_report_by_company_exception(mock_mongo):
    mock_client, mock_db, mock_collection = mock_mongo_hierarchy()
    mock_collection.find_one.side_effect = Exception("fail")
    mock_mongo.return_value = mock_client

    company = DummyCompany()
    db = MongCollection()
    with patch("src.db_utils.mongo.Document", DummyDocument):
        result = db.get_report_by_company(company)
        assert result is None

@patch("src.db_utils.mongo.MongoClient")
def test_get_available_companies_success(mock_mongo):
    mock_client, mock_db, mock_collection = mock_mongo_hierarchy()
    mock_collection.distinct.return_value = ["AAPL", "MSFT"]
    mock_mongo.return_value = mock_client

    db = MongCollection()
    result = db.get_available_companies()
    assert result == ["AAPL", "MSFT"]

@patch("src.db_utils.mongo.MongoClient")
def test_get_available_companies_exception(mock_mongo):
    mock_client, mock_db, mock_collection = mock_mongo_hierarchy()
    mock_collection.distinct.side_effect = Exception("fail")
    mock_mongo.return_value = mock_client

    db = MongCollection()
    result = db.get_available_companies()
    assert result == []

def test_get_available_years_int():
    db = MongCollection()
    doc = {"report_metadata": {"year": 2023}}
    assert db.get_available_years(doc) == [2023]

def test_get_available_years_str():
    db = MongCollection()
    doc = {"report_metadata": {"year": "2022"}}
    assert db.get_available_years(doc) == [2022]

def test_get_available_years_invalid():
    db = MongCollection()
    doc = {"report_metadata": {"year": "notayear"}}
    assert db.get_available_years(doc) == []

def test_get_available_years_missing():
    db = MongCollection()
    doc = {}
    assert db.get_available_years(doc) == []