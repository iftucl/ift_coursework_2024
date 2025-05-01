import pytest
from unittest.mock import patch, MagicMock
import json
from team_adansonia.coursework_two.validation.validation import (
    validate_and_clean_data,
    full_validation_pipeline
)


class TestValidation:
    """Test validation module functionality"""
    
    @pytest.fixture
    def mock_esg_data(self):
        """Mock ESG data"""
        return {
            "Scope Data": {
                "Scope 1": {
                    "2020": [100, "mtco2e"],
                    "2021": [95, "mtco2e"]
                },
                "Scope 2": {
                    "2020": [200, "mtco2e"],
                    "2021": [180, "mtco2e"]
                },
                "Invalid Metric": None
            },
            "Energy Data": {
                "Total Energy": {
                    "2020": [500, "mwh"],
                    "2021": [480, "mwh"]
                },
                "Renewable Energy": {
                    "2020": [100, "unknown unit"],
                    "2021": [120, "mwh"]
                }
            },
            "Water Data": {
                "Water Withdrawal": {
                    "2020": [1000, "thousand m3"],
                    "2021": [950, "thousand m3"]
                },
                "Out of Range Value": {
                    "2020": [1000000, "thousand m3"]
                },
                "Invalid Value": {
                    "2020": [None, "thousand m3"]
                }
            }
        }
    
    @pytest.fixture
    def mock_filtered_text(self):
        """Mock filtered text"""
        return """
        our scope 1 emissions were 100 mtco2e in 2020 and 95 mtco2e in 2021.
        our scope 2 emissions were 200 mtco2e in 2020 and 180 mtco2e in 2021.
        total energy consumption was 500 mwh in 2020 and 480 mwh in 2021.
        renewable energy was 100 [unit] in 2020 and 120 mwh in 2021.
        water withdrawal was 1000 thousand m3 in 2020 and 950 thousand m3 in 2021.
        """
    
    def test_validate_and_clean_data(self, mock_esg_data, mock_filtered_text):
        """Test data validation and cleaning"""
        cleaned, issues = validate_and_clean_data(mock_esg_data, mock_filtered_text)
        
        # Verify cleaned data structure
        assert "Scope Data" in cleaned
        assert "Energy Data" in cleaned
        assert "Water Data" in cleaned
        
        # Verify cleaning correctness
        assert cleaned["Scope Data"]["Scope 1"]["2020"] == 100
        assert cleaned["Scope Data"]["Scope 1"]["2021"] == 95
        assert "Units" in cleaned["Scope Data"]["Scope 1"]
        
        # Verify invalid data was removed
        assert "Invalid Metric" not in cleaned["Scope Data"]
        
        # Verify issues list
        assert len(issues) > 0
        assert any("Unrecognized unit" in issue["issue"] for issue in issues)
        assert any("Invalid Metric" in issue["metric"] for issue in issues)
        assert any("Out of range" in issue["issue"] for issue in issues)
    
    @patch("team_adansonia.coursework_two.validation.validation.validate_esg_data_with_deepseek")
    def test_full_validation_pipeline_success(self, mock_validate_deepseek, mock_esg_data, mock_filtered_text):
        """Test full validation pipeline success case"""
        # Setup mock
        corrected_data = {
            "Scope Data": {
                "Scope 1": {
                    "2020": 100,
                    "2021": 95,
                    "Units": "mtCO2e"
                }
            }
        }
        mock_validate_deepseek.return_value = corrected_data
        
        # Call function
        result = full_validation_pipeline(mock_esg_data, mock_filtered_text, "Test Company", "test.pdf")
        
        # Verify results
        assert result == corrected_data
        mock_validate_deepseek.assert_called_once()
    
    @patch("team_adansonia.coursework_two.validation.validation.validate_esg_data_with_deepseek")
    def test_full_validation_pipeline_fallback(self, mock_validate_deepseek, mock_esg_data, mock_filtered_text):
        """Test validation pipeline fallback when failure occurs"""
        # Setup mock
        mock_validate_deepseek.side_effect = Exception("API error")
        
        # Call function
        result = full_validation_pipeline(mock_esg_data, mock_filtered_text, "Test Company", "test.pdf")
        
        # Verify results
        assert result is not None
        assert "Scope Data" in result
        assert "Energy Data" in result
        mock_validate_deepseek.assert_called_once() 