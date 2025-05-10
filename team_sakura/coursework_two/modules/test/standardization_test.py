# tests/test_standardization.py
import pytest
from coursework_two.modules.utils.standardization import standardize_unit_value

@pytest.mark.parametrize("value, unit, expected_value, expected_unit", [
    # Mass conversions
    (100, "metric tonnes", 100, "tons"),
    (250, "metric tons", 250, "tons"),
    (10, "kilotons", 10000, "tons"),
    (5000, "kg", 5.0, "tons"),

    # Energy conversions
    (5, "mwh", 5000, "kwh"),
    (2, "gwh", 2000000, "kwh"),
    (3, "gigajoules", pytest.approx(833.334, rel=1e-6), "kwh"),

    # Water conversions
    (7, "thousand cubic meters (m3)", 7000, "cubic meters"),
    (4, "kilolitres", 4000, "liters"),

    # Waste conversions
    (6, "cubic yards", pytest.approx(4.5873294, rel=1e-6), "cubic meters"),

    # No conversion needed
    (123, None, 123, None),
    (999, "unknown unit", 999, "unknown unit"),
])
def test_standardize_unit_value(value, unit, expected_value, expected_unit):
    result_value, result_unit = standardize_unit_value(value, unit)
    assert result_value == expected_value
    assert result_unit == expected_unit