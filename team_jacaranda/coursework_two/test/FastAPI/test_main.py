# test/FastAPI/test_main.py
from fastapi.testclient import TestClient
from FastAPI.main import app
from unittest.mock import patch

client = TestClient(app)

@patch("FastAPI.main.query_db", return_value=[{"indicator_id": 1, "indicator_name": "Energy"}])
def test_get_indicators(mock_query):
    response = client.get("/indicators")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert response.json()[0]["indicator_name"] == "Energy"

@patch("FastAPI.main.query_db", return_value=[{"data_id": 1, "security": "ABC Corp"}])
def test_get_all_data(mock_query):
    response = client.get("/data")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

@patch("FastAPI.main.query_db", return_value=[])
def test_search_data_no_param(mock_query):
    response = client.get("/data/search")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

@patch("FastAPI.main.query_db", return_value=[])
def test_get_indicator_not_found(mock_query):
    response = client.get("/indicators/999999")  # 大概率不存在
    assert response.status_code == 404

@patch("FastAPI.main.query_db", return_value=[])
def test_root_frontend_redirect(mock_query):
    response = client.get("/")
    assert response.status_code in [200, 404]  # 静态资源目录未必存在

@patch("FastAPI.main.query_db", return_value=[{"id": 1, "symbol": "XYZ"}])
def test_get_reports(mock_query):
    response = client.get("/reports")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

@patch("FastAPI.main.query_db", return_value=[])
def test_search_reports(mock_query):
    response = client.get("/reports/search?symbol=XYZ")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

@patch("FastAPI.main.query_db", return_value=[])
def test_get_report_not_found(mock_query):
    response = client.get("/reports/99999")
    assert response.status_code == 404
