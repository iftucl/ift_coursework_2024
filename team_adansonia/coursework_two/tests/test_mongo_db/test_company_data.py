import pytest
from datetime import datetime
from team_adansonia.coursework_two.mongo_db.company_data import CompanyData, CompanyDatabase


class TestCompanyData:
    """Test CompanyData class"""

    def test_init(self):
        """Test CompanyData initialization"""
        company = CompanyData(
            symbol="TEST",
            security="Test Company",
            gics_sector="Technology",
            gics_industry="Software",
            country="US",
            region="North America"
        )
        
        assert company.symbol == "TEST"
        assert company.security == "Test Company"
        assert company.gics_sector == "Technology"
        assert company.gics_industry == "Software"
        assert company.country == "US"
        assert company.region == "North America"
        assert company.website_url is None
        assert company.csr_reports == {}
        assert isinstance(company.created_at, datetime)
        assert isinstance(company.updated_at, datetime)
    
    def test_init_with_optional_params(self):
        """Test CompanyData initialization with optional parameters"""
        company = CompanyData(
            symbol="TEST",
            security="Test Company",
            gics_sector="Technology",
            gics_industry="Software",
            country="US",
            region="North America",
            website_url="https://example.com",
            csr_reports={"2022": "https://example.com/csr/2022.pdf"}
        )
        
        assert company.website_url == "https://example.com"
        assert company.csr_reports == {"2022": "https://example.com/csr/2022.pdf"}
    
    def test_to_dict(self):
        """Test to_dict method"""
        company = CompanyData(
            symbol="TEST",
            security="Test Company",
            gics_sector="Technology",
            gics_industry="Software",
            country="US",
            region="North America"
        )
        
        company_dict = company.to_dict()
        assert company_dict["symbol"] == "TEST"
        assert company_dict["security"] == "Test Company"
        assert company_dict["gics_sector"] == "Technology"
        assert company_dict["gics_industry"] == "Software"
        assert company_dict["country"] == "US"
        assert company_dict["region"] == "North America"
        assert company_dict["website_url"] is None
        assert company_dict["csr_reports"] == {}
        assert "created_at" in company_dict
        assert "updated_at" in company_dict


class TestCompanyDatabase:
    """Test CompanyDatabase class"""
    
    def test_add_company(self, mongo_db, mock_company_data):
        """Test adding a company"""
        db = CompanyDatabase(mongo_db)
        db.add_company(mock_company_data)
        
        # Verify the company was added
        company_in_db = mongo_db.companies.find_one({"symbol": "TEST"})
        assert company_in_db is not None
        assert company_in_db["symbol"] == "TEST"
        assert company_in_db["security"] == "Test Company"
    
    def test_get_company(self, mongo_db, mock_company_data):
        """Test retrieving a company"""
        db = CompanyDatabase(mongo_db)
        db.add_company(mock_company_data)
        
        # Retrieve and verify the company
        retrieved_company = db.get_company("TEST")
        assert retrieved_company is not None
        assert retrieved_company.symbol == "TEST"
        assert retrieved_company.security == "Test Company"
        
        # Verify non-existent company returns None
        non_existent = db.get_company("NONEXISTENT")
        assert non_existent is None
    
    def test_update_gics_sector(self, mongo_db, mock_company_data):
        """Test updating GICS sector classification"""
        db = CompanyDatabase(mongo_db)
        db.add_company(mock_company_data)
        
        # Update sector classification
        db.update_gics_sector("TEST", "New Technology Sector")
        
        # Verify the update
        updated_company = db.get_company("TEST")
        assert updated_company.gics_sector == "New Technology Sector"
    
    def test_delete_company(self, mongo_db, mock_company_data):
        """Test deleting a company"""
        db = CompanyDatabase(mongo_db)
        db.add_company(mock_company_data)
        
        # Delete the company
        db.delete_company("TEST")
        
        # Verify deletion
        company = mongo_db.companies.find_one({"symbol": "TEST"})
        assert company is None 