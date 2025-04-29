# test/FastAPI/test_main.py
from fastapi.testclient import TestClient
from FastAPI.main import app
from unittest.mock import patch
import os

client = TestClient(app)

@patch("FastAPI.main.query_db", return_value=[{"indicator_id": 1, "indicator_name": "Energy"}])
def test_get_indicators(mock_query):
    response = client.get("/indicators")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert response.json()[0]["indicator_name"] == "Energy"

@patch("FastAPI.main.query_db", return_value=[])
def test_search_indicators_no_match(mock_query):
    response = client.get("/indicators/search?indicator_name=Water&theme=Climate")
    assert response.status_code == 200
    assert response.json() == []

@patch("FastAPI.main.query_db", return_value=[{"indicator_id": 1, "indicator_name": "Waste", "theme": "Climate"}])
def test_search_indicators_with_name_and_theme(mock_query):
    response = client.get("/indicators/search?indicator_name=Waste&theme=Climate")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

@patch("FastAPI.main.query_db", return_value=[{"indicator_id": 2, "indicator_name": "Water"}])
def test_get_indicator_by_id(mock_query):
    response = client.get("/indicators/2")
    assert response.status_code == 200
    assert response.json()["indicator_name"] == "Water"

@patch("FastAPI.main.query_db", return_value=[])
def test_get_indicator_not_found(mock_query):
    response = client.get("/indicators/999999")
    assert response.status_code == 404

@patch("FastAPI.main.query_db", return_value=[{"data_id": 1, "security": "ABC Corp"}])
def test_get_all_data(mock_query):
    response = client.get("/data")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

@patch("FastAPI.main.query_db", return_value=[])
def test_search_data_all_params(mock_query):
    response = client.get("/data/search?security=ABC&report_year=2023&indicator_id=1&indicator_name=Energy")
    assert response.status_code == 200
    assert response.json() == []

@patch("FastAPI.main.query_db", return_value=[])
def test_search_data_no_param(mock_query):
    response = client.get("/data/search")
    assert response.status_code == 200
    assert response.json() == []

@patch("FastAPI.main.query_db", return_value=[{"data_id": 100, "indicator_name": "CO2"}])
def test_get_data_by_id(mock_query):
    response = client.get("/data/100")
    assert response.status_code == 200
    assert response.json()["data_id"] == 100

@patch("FastAPI.main.query_db", return_value=[])
def test_get_data_by_id_not_found(mock_query):
    response = client.get("/data/999999")
    assert response.status_code == 404

@patch("FastAPI.main.query_db", return_value=[{"id": 1, "symbol": "XYZ"}])
def test_get_reports(mock_query):
    response = client.get("/reports")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

@patch("FastAPI.main.query_db", return_value=[{"id": 3, "symbol": "ZZZ", "security": "Example", "report_year": 2022}])
def test_search_reports_all_params(mock_query):
    response = client.get("/reports/search?symbol=ZZZ&security=Example&report_year=2022")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

@patch("FastAPI.main.query_db", return_value=[])
def test_search_reports(mock_query):
    response = client.get("/reports/search?symbol=XYZ")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

@patch("FastAPI.main.query_db", return_value=[{"id": 1, "symbol": "XYZ"}])
def test_get_company_report_by_id(mock_query):
    response = client.get("/reports/1")
    assert response.status_code == 200
    assert "symbol" in response.json()

@patch("FastAPI.main.query_db", return_value=[])
def test_get_report_not_found(mock_query):
    response = client.get("/reports/99999")
    assert response.status_code == 404

# 静态文件路径测试（根路径返回 index.html 或 404）
def test_root_frontend_redirect(monkeypatch):
    monkeypatch.setattr("os.path.exists", lambda x: True)
    monkeypatch.setattr("FastAPI.main.frontend_build_dir", "fakepath")

    response = client.get("/")
    assert response.status_code in [200, 404]  # 路径可能不存在文件

# favicon 路径存在与否都覆盖
def test_favicon(monkeypatch):
    monkeypatch.setattr("os.path.exists", lambda x: True)
    response = client.get("/favicon.ico")
    assert response.status_code in [200, 404]
