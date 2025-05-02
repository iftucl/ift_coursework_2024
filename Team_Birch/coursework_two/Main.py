"""
Main entrypoint for CSR data extraction pipeline.

Handles argument parsing, environment loading, MinIO connection, and PDF streaming.
"""

import subprocess
import sys
from argparse import ArgumentParser
from datetime import datetime
from pathlib import Path

import yaml

ROOT_DIR = Path(__file__).resolve().parent
SRC_PATH = ROOT_DIR / "src"
sys.path.insert(0, str(SRC_PATH))


from modules.input.minio_streaming_extractor import (
    connect_to_minio_from_env,
    stream_pdf_and_extract,
)
from modules.static.generate_data_catalogue import generate_catalogue_and_dictionary


def load_run_settings(settings_path: Path) -> dict:
    if not settings_path.exists():
        return {}

    with open(settings_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    return config.get("run_settings", {})


def run_mbh(script_name: str) -> None:
    """Run a Python script and report the result."""
    result = subprocess.run(["python", script_name])
    msg = (
        "succeeded" if result.returncode == 0 else f"failed (code {result.returncode})"
    )
    print(f"Script '{script_name}' {msg}.")


def main():
    """Main function to run the PDF extraction process."""
    parser = ArgumentParser(description="CSR Report Extractor")
    parser.add_argument(
        "--config",
        type=str,
        default="config/indicators.yaml",
        help="Path to indicators YAML config.",
    )
    parser.add_argument(
        "--output_csv",
        type=str,
        default="logs/final_output.csv",
        help="Path to output CSV file.",
    )
    parser.add_argument(
        "--log_path",
        type=str,
        default="logs/final_log.txt",
        help="Path to extraction log file.",
    )
    parser.add_argument(
        "--frequency",
        choices=["daily", "weekly", "monthly"],
        help="Run frequency control (overrides config).",
    )
    parser.add_argument(
        "--settings",
        type=str,
        default="config/conf.yaml",
        help="Path to run settings YAML file.",
    )

    args = parser.parse_args()

    config_path = Path(args.config)
    output_csv = Path(args.output_csv)
    log_path = Path(args.log_path)
    settings_path = Path(args.settings)

    # Load optional run settings
    run_settings = load_run_settings(settings_path)

    # Determine final frequency
    frequency = args.frequency or run_settings.get("frequency")
    if not frequency:
        raise ValueError(
            "Frequency must be provided either via CLI or in the config file."
        )

    print(f"[{datetime.now()}] Running extraction with frequency: {frequency}")
    print(f"Using config file: {config_path}")

    client = connect_to_minio_from_env()
    stream_pdf_and_extract(
        minio_client=client,
        bucket="csr-reports",
        config_path=config_path,
        output_csv=output_csv,
        log_path=log_path,
    )

    generate_catalogue_and_dictionary(
        config_path=config_path, output_dir=Path("static/")
    )

    run_mbh("modules/output/data_export.py")

    run_mbh("modules/output/data_clean.py")

    run_mbh("modules/output/data_storage.py")

    print("All processes completed.")


if __name__ == "__main__":
    main()
