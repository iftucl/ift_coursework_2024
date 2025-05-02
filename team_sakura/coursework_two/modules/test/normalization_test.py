# tests/test_normalizer.py
import pytest
from coursework_two.modules.utils.normalization import normalize_indicator_value, normalize_key


@pytest.mark.parametrize("input_text, expected", [
    ("27%", {"value": 27.0, "unit": "%"}),
    ("123,456 metric tons CO2-e", {"value": 123456, "unit": "metric tons CO2-e"}),
    ("N/A", {"value": None, "unit": None}),
    ("-", {"value": None, "unit": None}),
    ("", {"value": None, "unit": None}),
    ("42", {"value": 42, "unit": None}),
    (None, {"value": None, "unit": None}),
    ("invalid text", {"value": None, "unit": None}),
])
def test_normalize_indicator_value(input_text, expected):
    assert normalize_indicator_value(input_text) == expected

@pytest.mark.parametrize("input_key, expected", [
    ("CO2 Emissions", "co2_emissions"),
    ("  Leading Indicator ", "leading_indicator"),
    ("KEY WITH MULTIPLE SPACES", "key_with_multiple_spaces"),
])
def test_normalize_key(input_key, expected):
    assert normalize_key(input_key) == expected
