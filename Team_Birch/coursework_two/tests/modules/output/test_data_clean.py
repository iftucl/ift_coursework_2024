import importlib
from unittest import mock

import pandas as pd
import pytest


@pytest.mark.parametrize(
    "x,expected",
    [
        ("1 GWh", "1000 MWh"),
        ("0.5 TWh", "500000 MWh"),
        ("1000", "1000 MWh"),
        ("abc", ""),
        (None, ""),
    ],
)
def test_clean_energy_value(x, expected):
    from modules.output.data_clean import clean_energy_value

    assert clean_energy_value(x) == expected


@pytest.mark.parametrize(
    "cell,unit,expected",
    [
        ("123 tonnes CO₂", "tonnes CO₂", "123"),
        ("50 percent", "percent", "50"),
        ("invalid", "percent", ""),
        (None, "percent", ""),
    ],
)
def test_clean_and_strip_unit(cell, unit, expected):
    from modules.output.data_clean import clean_and_strip_unit

    assert clean_and_strip_unit(cell, unit) == expected


def test_data_clean_main_logic_runs():
    with mock.patch("pandas.read_csv") as mock_read_csv, mock.patch(
        "pandas.DataFrame.to_csv"
    ) as mock_to_csv:
        dummy_df = pd.DataFrame(
            {
                "Company Name": ["Apple", "Apple"],
                "Report Year": [2022, 2023],
                "Renewable Energy Usage": ["1 GWh", "0.5 TWh"],
                "Annual Carbon Emissions": ["123 tonnes CO₂", "456 tonnes CO₂"],
                "Annual Water Consumption": ["1000 cubic meters", "2000 cubic meters"],
                "Sustainable Materials Usage Ratio": ["80 percent", "101 percent"],
                "Waste Recycling Rate": ["60 percent", "70 percent"],
                "security": ["Apple Inc", "Apple Inc"],
            }
        )

        mock_read_csv.return_value = dummy_df.copy()

        import modules.output.data_clean as dc

        importlib.reload(dc)

        assert True
