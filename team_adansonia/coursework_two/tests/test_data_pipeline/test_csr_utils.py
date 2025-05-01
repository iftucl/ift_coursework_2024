import pytest
from unittest.mock import patch, MagicMock, mock_open
import io
from io import BytesIO
import requests
from team_adansonia.coursework_two.data_pipeline.csr_utils import (
    download_pdf, 
    filter_pdf_pages, 
    get_latest_report_year, 
    get_latest_report_url
)

class TestCsrUtils:
    """Test CSR utility functions"""
    
    @patch("team_adansonia.coursework_two.data_pipeline.csr_utils.requests.get")
    def test_download_pdf_success(self, mock_get):
        """Test successful PDF download"""
        # Setup mock
        mock_response = MagicMock()
        mock_response.content = b"PDF content"
        mock_get.return_value = mock_response
        
        # Call function
        result = download_pdf("https://example.com/report.pdf")
        
        # Verify results
        assert isinstance(result, BytesIO)
        result.seek(0)
        assert result.read() == b"PDF content"
        mock_get.assert_called_once_with("https://example.com/report.pdf", timeout=10)
    
    @patch("team_adansonia.coursework_two.data_pipeline.csr_utils.requests.get")
    def test_download_pdf_failure(self, mock_get):
        """Test PDF download failure"""
        # Setup mock
        mock_get.side_effect = requests.RequestException("Download error")
        
        # Call function
        result = download_pdf("https://example.com/bad-url.pdf")
        
        # Verify results
        assert result is None
        mock_get.assert_called_once()
    
    @patch("team_adansonia.coursework_two.data_pipeline.csr_utils.PdfReader")
    @patch("team_adansonia.coursework_two.data_pipeline.csr_utils.PdfWriter")
    @patch("team_adansonia.coursework_two.data_pipeline.csr_utils.pdfplumber.open")
    def test_filter_pdf_pages(self, mock_plumber_open, mock_writer, mock_reader):
        """Test PDF page filtering"""
        # Setup mock
        mock_pdf = MagicMock()
        mock_page = MagicMock()
        mock_page.extract_text.return_value = "This report contains energy usage in MWh for 2020 and 2021"
        mock_pdf.pages = [mock_page]
        mock_plumber_open.return_value.__enter__.return_value = mock_pdf
        
        mock_writer_instance = MagicMock()
        mock_writer.return_value = mock_writer_instance
        
        mock_reader_instance = MagicMock()
        mock_reader.return_value = mock_reader_instance
        mock_reader_instance.pages = [MagicMock()]
        
        # Call function
        pdf_data = BytesIO(b"Test PDF content")
        result_pdf, text = filter_pdf_pages(pdf_data)
        
        # Verify results
        assert isinstance(result_pdf, BytesIO)
        assert "energy usage" in text
        assert "mwh" in text
        assert "2020" in text
        assert "2021" in text
        mock_writer_instance.add_page.assert_called_once()
    
    def test_get_latest_report_year(self):
        """Test getting the latest report year"""
        # Test normal case
        reports = {2019: "url1", 2020: "url2", 2021: "url3"}
        assert get_latest_report_year(reports) == 2021
        
        # Test string years
        reports = {"2019": "url1", "2020": "url2", "2022": "url3"}
        assert get_latest_report_year(reports) == 2022
        
        # Test empty URLs
        reports = {2019: "url1", 2020: "", 2022: None}
        assert get_latest_report_year(reports) == 2019
        
        # Test empty dictionary
        assert get_latest_report_year({}) is None
        
        # Test non-dictionary
        assert get_latest_report_year(None) is None
        assert get_latest_report_year("not a dict") is None
    
    def test_get_latest_report_url(self):
        """Test getting the latest report URL"""
        # Test normal case
        reports = {2019: "url1", 2020: "url2", 2021: "url3"}
        assert get_latest_report_url(reports) == "url3"
        
        # Test specific year
        assert get_latest_report_url(reports, 2020) == "url2"
        
        # Test non-existent year
        assert get_latest_report_url(reports, 2022) is None
        
        # Test empty URLs
        reports = {2019: "url1", 2020: "", 2021: None}
        assert get_latest_report_url(reports) == "url1"
        
        # Test empty dictionary
        assert get_latest_report_url({}) is None
        
        # Test non-dictionary
        assert get_latest_report_url(None) is None 