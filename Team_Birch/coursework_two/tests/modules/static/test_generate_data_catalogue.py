import csv

import pytest
import yaml

from modules.static.generate_data_catalogue import generate_catalogue_and_dictionary


@pytest.fixture
def mock_indicator_config(tmp_path):
    config = [
        {
            "theme": "Environmental",
            "indicators": [
                {
                    "name": "Carbon Emissions",
                    "key": "carbon_emissions",
                    "unit": "tonnes CO₂",
                    "expected_type": "float",
                    "aim": "reduction",
                    "has_target": True,
                    "validation": {"min": 0, "max": 1_000_000, "warn_above": 900_000},
                    "aliases": ["CO2 Emissions", "Emissions"],
                }
            ],
        }
    ]

    config_path = tmp_path / "indicators.yaml"
    with open(config_path, "w") as f:
        yaml.dump(config, f)

    return config_path


def test_generate_catalogue_and_dictionary(tmp_path, mock_indicator_config):
    output_dir = tmp_path / "static"
    output_dir.mkdir()

    generate_catalogue_and_dictionary(
        config_path=mock_indicator_config, output_dir=output_dir
    )

    catalogue_file = output_dir / "data_catalogue.csv"
    dictionary_file = output_dir / "data_dictionary.csv"

    assert catalogue_file.exists()
    assert dictionary_file.exists()

    # Validate catalogue content
    with open(catalogue_file, newline="") as f:
        rows = list(csv.reader(f))
        assert rows[0] == ["Theme", "Indicator Name"]
        assert rows[1] == ["Environmental", "Carbon Emissions"]

    # Validate dictionary content
    with open(dictionary_file, newline="") as f:
        rows = list(csv.reader(f))
        assert rows[0][:3] == ["Theme", "Indicator Name", "Key"]
        assert rows[1][0] == "Environmental"
        assert rows[1][1] == "Carbon Emissions"
        assert rows[1][2] == "carbon_emissions"
