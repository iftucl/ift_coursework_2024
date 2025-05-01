import pytest
from unittest.mock import patch, MagicMock
import os
import json
from io import BytesIO
from team_adansonia.coursework_two.data_pipeline.csr_utils import download_pdf, filter_pdf_pages, get_latest_report_url
from team_adansonia.coursework_two.validation.validation import validate_and_clean_data, full_validation_pipeline
from team_adansonia.coursework_two.mongo_db.company_data import CompanyData, CompanyDatabase


@pytest.mark.e2e
class TestDataPipelineE2E:
    """End-to-end tests for the complete data processing pipeline"""
    
    @pytest.fixture
    def mock_company(self):
        """Mock company data"""
        return CompanyData(
            symbol="TEST",
            security="Test Company",
            gics_sector="Technology",
            gics_industry="Software",
            country="US",
            region="North America",
            website_url="https://example.com",
            csr_reports={"2022": "https://example.com/csr/2022.pdf"}
        )
    
    @patch("team_adansonia.coursework_two.data_pipeline.csr_utils.requests.get")
    @patch("team_adansonia.coursework_two.data_pipeline.csr_utils.PdfReader")
    @patch("team_adansonia.coursework_two.data_pipeline.csr_utils.PdfWriter")
    @patch("team_adansonia.coursework_two.data_pipeline.csr_utils.pdfplumber.open")
    @patch("team_adansonia.coursework_two.validation.validation.validate_esg_data_with_deepseek")
    def test_complete_data_pipeline(
        self, 
        mock_validate_deepseek,
        mock_plumber_open, 
        mock_writer, 
        mock_reader, 
        mock_requests_get,
        mock_company, 
        mongo_db
    ):
        """Test the complete data processing pipeline: from PDF download to storing validated data"""
        # Prepare test database
        db = CompanyDatabase(mongo_db)
        db.add_company(mock_company)
        
        # 1. Mock PDF download
        mock_response = MagicMock()
        mock_response.content = b"Mock PDF content"
        mock_requests_get.return_value = mock_response
        
        # 2. Mock PDF filtering
        mock_pdf = MagicMock()
        mock_page = MagicMock()
        mock_page.extract_text.return_value = """
        This is a sustainability report with ESG data.
        Scope 1 emissions were 100 mtco2e in 2020 and 95 mtco2e in 2021.
        Total energy consumption was 500 mwh in 2020 and 480 mwh in 2021.
        Water withdrawal was 1000 thousand m3 in 2020 and 950 thousand m3 in 2021.
        """
        mock_pdf.pages = [mock_page]
        mock_plumber_open.return_value.__enter__.return_value = mock_pdf
        
        mock_writer_instance = MagicMock()
        mock_writer.return_value = mock_writer_instance
        
        mock_reader_instance = MagicMock()
        mock_reader.return_value = mock_reader_instance
        mock_reader_instance.pages = [MagicMock()]
        
        # 3. Mock DeepSeek validation
        validated_data = {
            "Scope Data": {
                "Scope 1": {
                    "2020": 100,
                    "2021": 95,
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
        mock_validate_deepseek.return_value = validated_data
        
        # Test Step 1: Get the latest report URL
        report_url = get_latest_report_url(mock_company.csr_reports)
        assert report_url == "https://example.com/csr/2022.pdf"
        
        # Test Step 2: Download the report
        pdf_data = download_pdf(report_url)
        assert pdf_data is not None
        
        # Test Step 3: Filter the PDF
        filtered_pdf, filtered_text = filter_pdf_pages(pdf_data)
        assert "scope 1 emissions" in filtered_text
        
        # Mock extracted raw ESG data
        raw_esg_data = {
            "Scope Data": {
                "Scope 1": {
                    "2020": [100, "mtco2e"],
                    "2021": [95, "mtco2e"]
                }
            },
            "Energy Data": {
                "Total Energy": {
                    "2020": [500, "mwh"],
                    "2021": [480, "mwh"]
                }
            }
        }
        
        # Test Step 4: Validate the data
        validated_esg_data = full_validation_pipeline(
            raw_esg_data, 
            filtered_text,
            mock_company.security,
            "test.pdf"
        )
        
        assert validated_esg_data is not None
        assert "Scope Data" in validated_esg_data
        
        # Test Step 5: Update company data in the database
        mongo_db.companies.update_one(
            {"symbol": mock_company.symbol},
            {"$set": {"esg_data": validated_esg_data}}
        )
        
        # Verify database update
        updated_company = mongo_db.companies.find_one({"symbol": "TEST"})
        assert updated_company is not None
        assert "esg_data" in updated_company
        assert updated_company["esg_data"] == validated_esg_data 