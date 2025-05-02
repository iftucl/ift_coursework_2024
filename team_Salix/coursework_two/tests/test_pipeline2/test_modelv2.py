"""
Unit tests for Pipeline 2: Text Extraction Model
"""

import os
import sys
from pathlib import Path

import pytest

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from pipeline2.modules.modelv2 import data_formatting, extract_text_from_pdf


def test_text_extraction(sample_pdf_path):
    """Test text extraction from PDF"""
    text = extract_text_from_pdf(sample_pdf_path)
    assert isinstance(text, str)
    assert len(text) > 0


@pytest.mark.integration
def test_data_formatting():
    """Test data formatting functionality"""
    # Test tCO2e conversion
    assert float(data_formatting("1000 kg", "tCO2e")) == 1.0
    assert float(data_formatting("1 kt", "tCO2e")) == 1000.0
    assert float(data_formatting("1 mt", "tCO2e")) == 1000000.0

    # Test MWh conversion
    assert float(data_formatting("1000 kwh", "MWh")) == 1.0
    assert float(data_formatting("1 gwh", "MWh")) == 1000.0
    assert float(data_formatting("1 tj", "MWh")) == 277.78

    # Test m³ conversion
    assert float(data_formatting("1000 liters", "m³")) == 1.0
    assert float(data_formatting("1 km³", "m³")) == 1000000000.0

    # Test Metric tons conversion
    assert float(data_formatting("1000 kg", "Metric tons")) == 1.0
    assert float(data_formatting("1 kt", "Metric tons")) == 1000.0

    # Test percentage
    assert float(data_formatting("0.5", "%")) == 50.0
    assert float(data_formatting("50%", "%")) == 50.0


@pytest.mark.integration
def test_complete_extraction_pipeline(sample_pdf_path):
    """Integration test for the complete text extraction pipeline"""
    # Test the complete process
    text = extract_text_from_pdf(sample_pdf_path)
    assert isinstance(text, str)
    assert len(text) > 0

    # Test that the text contains some expected keywords
    text_lower = text.lower()
    assert any(
        keyword in text_lower
        for keyword in [
            "scope 1",
            "scope 2",
            "energy consumption",
            "water withdrawal",
            "waste generated",
            "employee diversity",
        ]
    )
