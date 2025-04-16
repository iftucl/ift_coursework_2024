import json
import os
import re
from dotenv import load_dotenv
from loguru import logger

#TODO: Check if value is in raw parsed text


load_dotenv()
LLAMA_API_KEY = os.getenv("LLAMA_API_KEY")

unit_config = {
    "Scope Data": [
        (r"^mtco2e?$", 1),  # Match "mtco2e" or "mtco2" (both singular and plural, case-insensitive)
        (r"^metric ton(s)? co2$", 1),  # Match "metric ton co2" or "metric tons co2"
        (r"^mmt.*co2$", 1_000_000),
        (r"^(thousands?|kilo|k)\s*of\s*metric\s*tons?\s*of?\s*co2[e]?$", 1_000),  # Thousands of metric tons
        (r"^(millions?|mega|m)\s*of\s*metric\s*tons?\s*of?\s*co2[e]?$", 1_000_000)
    ],
    "Energy Data": [
        (r"^mwh$", 1),  # Match "mwh" for megawatt-hours (case-insensitive)
        (r"^megawatt[- ]?hours?$", 1),  # Match "megawatt-hours" with optional space or hyphen
        (r"^kwh$", 0.001),  # Match "kwh" for kilowatt-hours (scale factor 0.001)
        (r"^kilowatt[- ]?hours?$", 0.001),  # Match "kilowatt-hours" with optional space or hyphen
        (r"^thousand mwh$", 1_000),  # Match "thousand mwh"
        (r"^1000 mwh$", 1_000),  # Match "1000 mwh"
    ],
    "Water Data": [
        (r"^thousand m(3|\u00b3)$", 1),  # Match "thousand m3" or "thousand m³" (for cubic meters)
        (r"^m(3|\u00b3)$", 0.001),  # Match "m3" or "m³" (for cubic meters, scaling to thousand cubic meters)
        (r"^gallons?$", 0.003785),  # Match "gallon" or "gallons" (convert to liters)
        (r"^million gallons?$", 3_785.41),  # Match "million gallons"
        (r"^m(m)?gal$", 3_785.41),  # Match "mgal" or "mmgal" (million gallons)
    ],
}


expected_ranges = {
    "Scope Data": (0, 10_000_000),
    "Energy Data": (0, 20_000_000),
    "Water Data": (0, 100_000),
}

def validate_and_clean_data(raw_data: dict):
    cleaned = {}
    issues = []

    logger.debug(f"Raw data structure: {json.dumps(raw_data, indent=2)}")

    for category, metrics in raw_data.items():
        cleaned[category] = {}
        unit_patterns = unit_config.get(category, [])
        min_base, max_base = expected_ranges.get(category, (None, None))

        for metric, yearly_data in metrics.items():
            if yearly_data is None:
                logger.warning("Skipping None metric.")
                continue
            cleaned[category][metric] = {}
            units = None  # Track original unit

            for year, pair in yearly_data.items():
                if not isinstance(pair, list) or len(pair) != 2:
                    continue

                value, unit = pair

                if value is None or unit is None:
                    # Log the missing data for better visibility
                    logger.warning(f"Skipping {metric} for {year} due to missing value or unit.")
                    continue

                # Debug print for value and unit
                logger.debug(f"Processing value: {value}, unit: {unit} for metric: {metric}, year: {year}")

                normalized_unit = unit.strip().lower()
                base_value = None
                matched = False

                # Try matching known unit patterns
                for pattern, scale in unit_patterns:
                    if re.search(pattern, normalized_unit):
                        matched = True
                        base_value = value * scale  # used only for range check

                        if min_base is not None and max_base is not None:
                            if not (min_base <= base_value <= max_base):
                                issues.append({
                                    "category": category,
                                    "metric": metric,
                                    "year": year,
                                    "issue": f"Out of range: {base_value} (expected {min_base}-{max_base})"
                                })

                        # Keep original value and unit
                        cleaned[category][metric][year] = value
                        if units is None:
                            units = unit
                        break

                if not matched:
                    # Log unrecognized unit issue
                    cleaned[category][metric][year] = value
                    if units is None:
                        units = unit  # keep the original unit string
                    issues.append({
                        "category": category,
                        "metric": metric,
                        "year": year,
                        "issue": f"Unrecognized unit: '{unit}'"
                    })

            # Attach unit label after all years
            if units:
                cleaned[category][metric]["Units"] = units

            # If all years were invalid (very unlikely now), remove the metric
            if not any(k for k in cleaned[category][metric] if k != "Units"):
                del cleaned[category][metric]

    print(json.dumps(cleaned, indent=2))
    return cleaned, issues
