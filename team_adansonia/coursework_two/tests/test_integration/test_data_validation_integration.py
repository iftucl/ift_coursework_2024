import pytest
from unittest.mock import patch, MagicMock
import json
import os
from io import BytesIO
from data_pipeline.csr_utils import filter_pdf_pages
from validation.validation import validate_and_clean_data, full_validation_pipeline


class TestDataValidationIntegration:
    """Test integration between data processing and validation"""
    
    @pytest.fixture
    def mock_pdf_content(self):
        """Create mock PDF content"""
        return BytesIO(b"Test PDF content with ESG data")
    
    @pytest.fixture
    def mock_esg_data(self):
        """Create mock ESG data"""
        return {
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
            },
            "Water Data": {
                "Water Withdrawal": {
                    "2020": [1000, "thousand m3"],
                    "2021": [950, "thousand m3"]
                }
            }
        }
    
    @patch("team_adansonia.coursework_two.data_pipeline.csr_utils.PdfReader")
    @patch("team_adansonia.coursework_two.data_pipeline.csr_utils.PdfWriter")
    @patch("team_adansonia.coursework_two.data_pipeline.csr_utils.pdfplumber.open")
    def test_pdf_filtering_to_validation(self, mock_plumber_open, mock_writer, mock_reader, mock_pdf_content, mock_esg_data):
        """Test workflow from PDF filtering to data validation"""
        # Setup mocks for PDF filtering
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
        
        # Execute PDF filtering
        filtered_pdf, filtered_text = filter_pdf_pages(mock_pdf_content)
        
        # Verify filtering results
        assert "scope 1 emissions" in filtered_text
        assert "100 mtco2e" in filtered_text
        assert "energy consumption" in filtered_text
        
        # Setup mocks for validation
        with patch("team_adansonia.coursework_two.validation.validation.validate_esg_data_with_deepseek") as mock_deepseek:
            # Setup DeepSeek validation results
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
                },
                "Water Data": {
                    "Water Withdrawal": {
                        "2020": 1000,
                        "2021": 950,
                        "Units": "thousand m3"
                    }
                }
            }
            mock_deepseek.return_value = validated_data
            
            # Execute validation process
            result = full_validation_pipeline(mock_esg_data, filtered_text, "Test Company", "test.pdf")
            
            # Verify results
            assert result == validated_data
            mock_deepseek.assert_called_once()
    
    def test_data_cleaning_validation(self, mock_esg_data):
        """Test data cleaning and validation logic"""
        # Create text with raw data
        filtered_text = """
        scope 1 emissions were 100 mtco2e in 2020 and 95 mtco2e in 2021.
        total energy was 500 mwh in 2020 and 480 mwh in 2021.
        water withdrawal was 1000 thousand m3 in 2020 and 950 thousand m3 in 2021.
        """
        
        # Execute validation and cleaning
        cleaned_data, issues = validate_and_clean_data(mock_esg_data, filtered_text)
        
        # Verify results
        assert cleaned_data["Scope Data"]["Scope 1"]["2020"] == 100
        assert cleaned_data["Scope Data"]["Scope 1"]["2021"] == 95
        assert cleaned_data["Energy Data"]["Total Energy"]["2020"] == 500
        assert cleaned_data["Water Data"]["Water Withdrawal"]["2020"] == 1000 