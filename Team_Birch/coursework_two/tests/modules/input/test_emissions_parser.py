from pathlib import Path
from unittest.mock import MagicMock, patch

from src.modules.input.emissions_parser import extract_indicators_from_bytes


def test_extract_indicators_basic(tmp_path):
    sample_text = "Carbon Emissions: 1,000 tonnes\nWater Use: 500,000 liters"

    class DummyPage:
        def extract_text(self):
            return sample_text

    class DummyPdfReader:
        def __init__(self, *args, **kwargs):
            self.pages = [DummyPage(), DummyPage()]

    indicator_config = [
        {
            "group": "Environment",
            "indicators": [
                {
                    "name": "Carbon Emissions",
                    "aliases": ["CO2 Emissions"],
                    "unit": "tonnes",
                    "validation": {},
                    "expected_type": "float",
                    "aim": "reduction",
                },
                {
                    "name": "Water Use",
                    "aliases": ["Water Consumption"],
                    "unit": "liters",
                    "validation": {},
                    "expected_type": "float",
                    "aim": "reduction",
                },
            ],
        }
    ]

    with patch("src.modules.input.emissions_parser.PdfReader", DummyPdfReader), patch(
        "src.modules.input.emissions_parser.load_indicator_config",
        return_value=indicator_config,
    ), patch(
        "src.modules.input.emissions_parser.query_deepseek",
        side_effect=[
            "Report Year: 2022",  # header metadata
            """Company Name: Acme Corp
- Carbon Emissions: 1,000 tonnes
- Water Use: 500,000 liters""",
        ],
    ), patch(
        "src.modules.input.emissions_parser.postprocess_value",
        side_effect=lambda val, *_args, **_kwargs: {
            "normalized": val,
            "valid": True,
            "warning": False,
        },
    ):
        result, lineage, *_ = extract_indicators_from_bytes(
            company_name="TestCo",
            pdf_bytes=MagicMock(),  # skipped by mock PdfReader
            config_path=Path("fake.yaml"),
            output_csv=tmp_path / "output.csv",
            log_path=tmp_path / "log.txt",
            source_filename="mock_report.pdf",
        )

    assert result == {
        "Carbon Emissions": "1,000 tonnes",
        "Water Use": "500,000 liters",
    }

    assert len(lineage) == 2
    assert all(rec["value"] in ["1,000 tonnes", "500,000 liters"] for rec in lineage)
    assert all(rec["company_name"] == "Acme Corp" for rec in lineage)
    assert all(rec["report_year"] == "2022" for rec in lineage)


def test_extract_no_relevant_text(tmp_path):
    class DummyPage:
        def extract_text(self):
            return "Some completely unrelated text about finances."

    class DummyPdfReader:
        def __init__(self, *args, **kwargs):
            self.pages = [DummyPage()]

    dummy_config = [
        {
            "group": "Environment",
            "indicators": [
                {
                    "name": "Carbon Emissions",
                    "aliases": ["CO2"],
                    "unit": "tonnes",
                    "validation": {},
                }
            ],
        }
    ]

    with patch("src.modules.input.emissions_parser.PdfReader", DummyPdfReader), patch(
        "src.modules.input.emissions_parser.load_indicator_config",
        return_value=dummy_config,
    ), patch(
        "src.modules.input.emissions_parser.query_deepseek",
        return_value="Report Year: 2021",
    ):
        result, lineage, *_ = extract_indicators_from_bytes(
            company_name="IrrelevantCo",
            pdf_bytes=MagicMock(),
            config_path=Path("fake.yaml"),
            output_csv=tmp_path / "output.csv",
            log_path=tmp_path / "log.txt",
            source_filename="unrelated_report.pdf",
        )

    assert result == {}
    assert lineage == []
