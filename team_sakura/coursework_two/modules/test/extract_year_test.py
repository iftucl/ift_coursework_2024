# tests/test_year_extraction.py
import pytest
from coursework_two.modules.utils.year_extraction import extract_year

@pytest.mark.parametrize("input_text, expected_year", [
    # Direct 4-digit year
    ("2023", 2023),
    ("In the year 2025 we achieved...", 2025),
    ("2023-2024", 2023),

    # FY formats
    ("FY23", 2023),
    ("FY 23", 2023),
    ("FY-23", 2023),


    # No year found
    ("No year here", None),
    ("FY", None),
    (None, None),
])
def test_extract_year(input_text, expected_year):
    assert extract_year(input_text) == expected_year
