import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
from fast_api.app import app
from mongo_db.company_data import CompanyData, CompanyDatabase


class TestMongoApiIntegration:
    """Test integration between MongoDB and API"""
    
    @pytest.fixture
    def company_data(self):
        """Create test company data"""
        return CompanyData(
            symbol="AAPL",
            security="Apple Inc.",
            gics_sector="Technology",
            gics_industry="Electronics",
            country="US",
            region="North America",
            website_url="https://www.apple.com",
            csr_reports={"2022": "https://example.com/reports/apple2022.pdf"}
        )
    
    @patch("team_adansonia.coursework_two.fast_api.app.get_db")
    def test_api_mongo_integration(self, mock_get_db, mongo_db, company_data):
        """Test API and MongoDB integration"""
        # Prepare test database
        db = CompanyDatabase(mongo_db)
        db.add_company(company_data)
        
        # Mock API database connection
        mock_get_db.return_value = mongo_db
        
        # Create test client
        client = TestClient(app)
        
        # Test API call
        response = client.get("/companies/AAPL")
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["symbol"] == "AAPL"
        assert data["security"] == "Apple Inc."
        assert data["gics_sector"] == "Technology"
        
        # Test API request for non-existent company
        response = client.get("/companies/NONEXISTENT")
        assert response.status_code == 404 