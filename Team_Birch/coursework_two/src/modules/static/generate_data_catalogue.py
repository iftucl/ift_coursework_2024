import csv
from pathlib import Path

import yaml


def load_indicator_config(config_path: Path) -> list:
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def generate_catalogue_and_dictionary(config_path: Path, output_dir: Path):
    indicators = load_indicator_config(config_path)

    # Prepare output files
    catalogue_path = output_dir / "data_catalogue.csv"
    dictionary_path = output_dir / "data_dictionary.csv"

    output_dir.mkdir(parents=True, exist_ok=True)

    # Write Data Catalogue (list of indicators)
    with open(catalogue_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Theme", "Indicator Name"])
        for group in indicators:
            theme = group.get("theme", "Unknown Theme")
            for ind in group.get("indicators", []):
                writer.writerow([theme, ind["name"]])

    # Write Data Dictionary (detailed info)
    with open(dictionary_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "Theme",
                "Indicator Name",
                "Key",
                "Unit",
                "Expected Type",
                "Aim",
                "Has Target",
                "Min",
                "Max",
                "Warn Above",
                "Aliases",
            ]
        )
        for group in indicators:
            theme = group.get("theme", "Unknown Theme")
            for ind in group.get("indicators", []):
                validation = ind.get("validation", {})
                writer.writerow(
                    [
                        theme,
                        ind["name"],
                        ind.get("key", ""),
                        ind.get("unit", ""),
                        ind.get("expected_type", ""),
                        ind.get("aim", ""),
                        ind.get("has_target", False),
                        validation.get("min", ""),
                        validation.get("max", ""),
                        validation.get("warn_above", ""),
                        "; ".join(ind.get("aliases", [])),
                    ]
                )

    print(f"Data catalogue generated at: {catalogue_path}")
    print(f" Data dictionary generated at: {dictionary_path}")


if __name__ == "__main__":
    config_path = Path("config/indicators.yaml")
    output_dir = Path("static/")
    generate_catalogue_and_dictionary(config_path, output_dir)
