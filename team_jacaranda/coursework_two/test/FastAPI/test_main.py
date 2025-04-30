"""
Module: test_main

This module contains test cases for the FastAPI application endpoints.
It uses pytest and unittest.mock to test various endpoints that interact
with a database, returning indicator, data, and report information. The tests
cover scenarios such as successful retrieval, search with parameters, and error handling.

Each test mocks the database query (`query_db`) to return predefined values,
allowing for consistent and controlled test execution.

Test cases include:
- Retrieving all indicators.
- Searching for indicators by name or theme.
- Retrieving data by ID.
- Searching for data based on multiple parameters.
- Handling of reports and errors (e.g., not found).

The tests verify the status codes, response structures, and expected behaviors of the API.
"""

from fastapi.testclient import TestClient
from FastAPI.main import app
from unittest.mock import patch
import os

client = TestClient(app)

@patch("FastAPI.main.query_db", return_value=[{"indicator_id": 1, "indicator_name": "Energy"}])
def test_get_indicators(mock_query):
    """
    Test the GET /indicators endpoint.

    This test ensures that the endpoint returns a list of indicators with the correct structure.
    It verifies that the response status is 200 and that the 'indicator_name' of the first item is "Energy".

    :param mock_query: The mocked query_db function used to return predefined data.
    """
    response = client.get("/indicators")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert response.json()[0]["indicator_name"] == "Energy"

@patch("FastAPI.main.query_db", return_value=[])
def test_search_indicators_no_match(mock_query):
    """
    Test the GET /indicators/search endpoint with no matching indicators.

    This test ensures that when no matching indicators are found, the response is an empty list.
    It verifies that the response status is 200 and the JSON body is an empty list.

    :param mock_query: The mocked query_db function used to return an empty list.
    """
    response = client.get("/indicators/search?indicator_name=Water&theme=Climate")
    assert response.status_code == 200
    assert response.json() == []

@patch("FastAPI.main.query_db", return_value=[{"indicator_id": 1, "indicator_name": "Waste", "theme": "Climate"}])
def test_search_indicators_with_name_and_theme(mock_query):
    """
    Test the GET /indicators/search endpoint with matching indicators.

    This test ensures that the endpoint returns matching indicators when searching by name and theme.
    It verifies that the response status is 200 and the returned data is a list.

    :param mock_query: The mocked query_db function used to return predefined matching data.
    """
    response = client.get("/indicators/search?indicator_name=Waste&theme=Climate")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

@patch("FastAPI.main.query_db", return_value=[{"indicator_id": 2, "indicator_name": "Water"}])
def test_get_indicator_by_id(mock_query):
    """
    Test the GET /indicators/{id} endpoint by ID.

    This test ensures that the endpoint correctly retrieves an indicator by its ID.
    It verifies that the response status is 200 and that the indicator name matches "Water".

    :param mock_query: The mocked query_db function used to return predefined data for the specified ID.
    """
    response = client.get("/indicators/2")
    assert response.status_code == 200
    assert response.json()["indicator_name"] == "Water"

@patch("FastAPI.main.query_db", return_value=[])
def test_get_indicator_not_found(mock_query):
    """
    Test the GET /indicators/{id} endpoint when the indicator is not found.

    This test ensures that the endpoint returns a 404 status code when the requested indicator does not exist.

    :param mock_query: The mocked query_db function used to simulate no data being found.
    """
    response = client.get("/indicators/999999")
    assert response.status_code == 404

@patch("FastAPI.main.query_db", return_value=[{"data_id": 1, "security": "ABC Corp"}])
def test_get_all_data(mock_query):
    """
    Test the GET /data endpoint.

    This test ensures that the endpoint returns a list of data items with the correct structure.
    It verifies that the response status is 200 and that the returned data is a list.

    :param mock_query: The mocked query_db function used to return predefined data.
    """
    response = client.get("/data")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

@patch("FastAPI.main.query_db", return_value=[])
def test_search_data_all_params(mock_query):
    """
    Test the GET /data/search endpoint with all search parameters.

    This test ensures that the endpoint returns no data when searching with specific parameters.
    It verifies that the response status is 200 and the returned data is an empty list.

    :param mock_query: The mocked query_db function used to simulate no data matching the search parameters.
    """
    response = client.get("/data/search?security=ABC&report_year=2023&indicator_id=1&indicator_name=Energy")
    assert response.status_code == 200
    assert response.json() == []

@patch("FastAPI.main.query_db", return_value=[])
def test_search_data_no_param(mock_query):
    """
    Test the GET /data/search endpoint with no search parameters.

    This test ensures that the endpoint returns an empty list when no parameters are provided.
    It verifies that the response status is 200 and the returned data is an empty list.

    :param mock_query: The mocked query_db function used to simulate no data when no parameters are provided.
    """
    response = client.get("/data/search")
    assert response.status_code == 200
    assert response.json() == []

@patch("FastAPI.main.query_db", return_value=[{"data_id": 100, "indicator_name": "CO2"}])
def test_get_data_by_id(mock_query):
    """
    Test the GET /data/{id} endpoint by ID.

    This test ensures that the endpoint correctly retrieves data by its ID.
    It verifies that the response status is 200 and the data ID is 100.

    :param mock_query: The mocked query_db function used to return predefined data for the specified ID.
    """
    response = client.get("/data/100")
    assert response.status_code == 200
    assert response.json()["data_id"] == 100

@patch("FastAPI.main.query_db", return_value=[])
def test_get_data_by_id_not_found(mock_query):
    """
    Test the GET /data/{id} endpoint when the data is not found.

    This test ensures that the endpoint returns a 404 status code when the requested data is not found.

    :param mock_query: The mocked query_db function used to simulate no data being found.
    """
    response = client.get("/data/999999")
    assert response.status_code == 404

@patch("FastAPI.main.query_db", return_value=[{"id": 1, "symbol": "XYZ"}])
def test_get_reports(mock_query):
    """
    Test the GET /reports endpoint.

    This test ensures that the endpoint returns a list of reports with the correct structure.
    It verifies that the response status is 200 and the returned data is a list.

    :param mock_query: The mocked query_db function used to return predefined data.
    """
    response = client.get("/reports")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

@patch("FastAPI.main.query_db", return_value=[{"id": 3, "symbol": "ZZZ", "security": "Example", "report_year": 2022}])
def test_search_reports_all_params(mock_query):
    """
    Test the GET /reports/search endpoint with all search parameters.

    This test ensures that the endpoint returns matching reports when searching with specific parameters.
    It verifies that the response status is 200 and the returned data is a list.

    :param mock_query: The mocked query_db function used to return predefined data for the search parameters.
    """
    response = client.get("/reports/search?symbol=ZZZ&security=Example&report_year=2022")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

@patch("FastAPI.main.query_db", return_value=[])
def test_search_reports(mock_query):
    """
    Test the GET /reports/search endpoint with a partial search parameter.

    This test ensures that the endpoint returns a list of reports even when only a partial search parameter is provided.
    It verifies that the response status is 200 and the returned data is a list.

    :param mock_query: The mocked query_db function used to return predefined data for the search.
    """
    response = client.get("/reports/search?symbol=XYZ")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

@patch("FastAPI.main.query_db", return_value=[{"id": 1, "symbol": "XYZ"}])
def test_get_company_report_by_id(mock_query):
    """
    Test the GET /reports/{id} endpoint by report ID.

    This test ensures that the endpoint correctly retrieves a report by its ID.
    It verifies that the response status is 200 and the report contains the 'symbol' field.

    :param mock_query: The mocked query_db function used to return predefined data for the specified report ID.
    """
    response = client.get("/reports/1")
    assert response.status_code == 200
    assert "symbol" in response.json()

@patch("FastAPI.main.query_db", return_value=[])
def test_get_report_not_found(mock_query):
    """
    Test the GET /reports/{id} endpoint when the report is not found.

    This test ensures that the endpoint returns a 404 status code when the requested report is not found.

    :param mock_query: The mocked query_db function used to simulate no data being found.
    """
    response = client.get("/reports/99999")
    assert response.status_code == 404

def test_root_frontend_redirect(monkeypatch):
    """
    Test the root URL for frontend redirect behavior.

    This test ensures that the root URL either returns index.html or a 404 error depending on the 
    availability of the frontend build directory. The test mocks the existence of the directory.

    :param monkeypatch: A pytest fixture that allows patching functions for testing purposes.
    """
    monkeypatch.setattr("os.path.exists", lambda x: True)
    monkeypatch.setattr("FastAPI.main.frontend_build_dir", "fakepath")
    response = client.get("/")
    assert response.status_code in [200, 404]  # Path may not exist

def test_favicon(monkeypatch):
    """
    Test the favicon endpoint.

    This test ensures that the favicon URL returns a valid response (either 200 or 404) depending 
    on the existence of the favicon file.

    :param monkeypatch: A pytest fixture that allows patching functions for testing purposes.
    """
    monkeypatch.setattr("os.path.exists", lambda x: True)
    response = client.get("/favicon.ico")
    assert response.status_code in [200, 404]
