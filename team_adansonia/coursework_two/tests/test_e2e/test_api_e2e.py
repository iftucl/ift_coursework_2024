import pytest
import json
from fastapi.testclient import TestClient
from unittest.mock import patch
from team_adansonia.coursework_two.fast_api.app import app
from team_adansonia.coursework_two.mongo_db.company_data import CompanyData, CompanyDatabase


@pytest.mark.e2e
class TestApiE2E:
    """API end-to-end tests"""
    
    @pytest.fixture
    def companies_data(self):
        """Create multiple test company data"""
        companies = [
            CompanyData(
                symbol="AAPL",
                security="Apple Inc.",
                gics_sector="Technology",
                gics_industry="Electronics",
                country="US",
                region="North America",
                website_url="https://www.apple.com",
                csr_reports={"2022": "https://example.com/reports/apple2022.pdf"}
            ),
            CompanyData(
                symbol="MSFT",
                security="Microsoft Corporation",
                gics_sector="Technology",
                gics_industry="Software",
                country="US",
                region="North America",
                website_url="https://www.microsoft.com",
                csr_reports={"2022": "https://example.com/reports/microsoft2022.pdf"}
            ),
            CompanyData(
                symbol="GOOGL",
                security="Alphabet Inc.",
                gics_sector="Technology",
                gics_industry="Internet",
                country="US",
                region="North America",
                website_url="https://www.google.com",
                csr_reports={"2022": "https://example.com/reports/google2022.pdf"}
            )
        ]
        
        # Add ESG data
        companies[0].esg_data = {
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
        
        companies[1].esg_data = {
            "Scope Data": {
                "Scope 1": {
                    "2020": 120,
                    "2021": 110,
                    "Units": "mtCO2e"
                }
            },
            "Water Data": {
                "Water Withdrawal": {
                    "2020": 1000,
                    "2021": 950,
                    "Units": "thousand m3"
                }
            }
        }
        
        return companies
    
    @patch("team_adansonia.coursework_two.fast_api.app.get_db")
    def test_api_complete_flow(self, mock_get_db, mongo_db, companies_data):
        """Test complete API workflow"""
        # Prepare test database
        db = CompanyDatabase(mongo_db)
        for company in companies_data:
            # Manually build dictionary to add ESG data
            company_dict = company.to_dict()
            if hasattr(company, 'esg_data'):
                company_dict["esg_data"] = company.esg_data
            mongo_db.companies.insert_one(company_dict)
        
        # Mock API database connection
        mock_get_db.return_value = mongo_db
        
        # Create test client
        client = TestClient(app)
        
        # Test getting all companies
        for company in companies_data:
            # Test getting specific company
            response = client.get(f"/companies/{company.symbol}")
            
            # Verify response
            assert response.status_code == 200
            data = response.json()
            assert data["symbol"] == company.symbol
            assert data["security"] == company.security
            
            if hasattr(company, 'esg_data'):
                assert "esg_data" in data
                
                # Test filtering by year
                response_year = client.get(f"/companies/{company.symbol}?year=2020")
                assert response_year.status_code == 200
                year_data = response_year.json()
                assert year_data["year"] == "2020"
                
                # Verify only 2020 data is returned
                if "Scope Data" in year_data["esg_data"] and "Scope 1" in year_data["esg_data"]["Scope Data"]:
                    scope1_data = year_data["esg_data"]["Scope Data"]["Scope 1"]
                    assert scope1_data == company.esg_data["Scope Data"]["Scope 1"]["2020"]
        
        # Test non-existent company
        response = client.get("/companies/NONEXISTENT")
        assert response.status_code == 404 