import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from fast_api.app import app


@pytest.fixture
def mock_db():
    """Mock database"""
    mock_db = MagicMock()
    return mock_db


@pytest.fixture
def mock_company():
    """Mock company data"""
    return {
        "symbol": "AAPL", 
        "security": "Apple Inc.", 
        "gics_sector": "Technology", 
        "gics_industry": "Electronics", 
        "country": "US", 
        "region": "North America",
        "esg_data": {
            "Scope Data": {
                "Scope 1": {
                    "2020": 100,
                    "2021": 95,
                    "Units": "mtCO2e"
                },
                "Scope 2": {
                    "2020": 200,
                    "2021": 180,
                    "Units": "mtCO2e"
                }
            },
            "Energy Data": {
                "Total Energy": {
                    "2020": 500,
                    "2021": 480,
                    "Units": "MWh"
                }
            }
        }
    }


class TestApp:
    """Test FastAPI application"""

    @patch("team_adansonia.coursework_two.fast_api.app.get_db")
    def test_get_company_found(self, mock_get_db, mock_company, mock_db):
        """Test finding an existing company"""
        # Setup mock
        mock_get_db.return_value = mock_db
        mock_db["companies"].find_one.return_value = mock_company
        
        # Create test client
        client = TestClient(app)
        
        # Test request
        response = client.get("/companies/AAPL")
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["symbol"] == "AAPL"
        assert data["security"] == "Apple Inc."
        assert "esg_data" in data
    
    @patch("team_adansonia.coursework_two.fast_api.app.get_db")
    def test_get_company_not_found(self, mock_get_db, mock_db):
        """Test finding a non-existent company"""
        # Setup mock
        mock_get_db.return_value = mock_db
        mock_db["companies"].find_one.return_value = None
        
        # Create test client
        client = TestClient(app)
        
        # Test request
        response = client.get("/companies/NONEXISTENT")
        
        # Verify response
        assert response.status_code == 404
        assert "detail" in response.json()
        assert response.json()["detail"] == "Company not found"
    
    @patch("team_adansonia.coursework_two.fast_api.app.get_db")
    def test_get_company_with_year(self, mock_get_db, mock_company, mock_db):
        """Test finding company data by year"""
        # Setup mock
        mock_get_db.return_value = mock_db
        mock_db["companies"].find_one.return_value = mock_company
        
        # Create test client
        client = TestClient(app)
        
        # Test request
        response = client.get("/companies/AAPL?year=2020")
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["symbol"] == "AAPL"
        assert data["year"] == "2020"
        assert "esg_data" in data
        
        # Verify only 2020 data is returned
        scope_data = data["esg_data"]["Scope Data"]
        assert scope_data["Scope 1"] == 100
        assert scope_data["Scope 2"] == 200 