"""
Handles normalization, validation, and postprocessing of extracted CSR indicator values.
"""

import logging
import re

logger = logging.getLogger(__name__)

UNIT_NORMALIZATION = {
    r"\btco\b": "tonnes CO",
    r"\bmt\s?co2e?\b": "tonnes CO₂",
    r"\bco2e\b": "tonnes CO₂",
    r"\bmetric tons?\b": "tonnes CO₂",
    r"\btons?\b": "tonnes CO₂",
    r"\btonnes?\b": "tonnes CO₂",
    r"\bkt\b": "kilotonnes",
    r"\bkilotons?\b": "kilotonnes",
    r"\bkilotonnes?\b": "kilotonnes",
    r"\bkg\b": "kg",
    r"\bkilograms?\b": "kg",
    r"\bmillion cubic meters?\b": "million m³",
    r"\bMCM\b": "million m³",
    r"\bgallons?\b": "gallons",
    r"\bcubic meters?\b": "m³",
    r"\bm\s*3\b": "m³",
    r"\bgigajoules?\b": "GJ",
    r"\bmegajoules?\b": "MJ",
    r"\bkilowatt[-\s]?hours?\b": "kWh",
    r"\bMWh\b": "MWh",
    r"\bGWh\b": "GWh",
    r"\bTWh\b": "TWh",
    r"\bgigawatts?\b": "GW",
    r"\bmegawatts?\b": "MW",
    r"\bkilowatts?\b": "kW",
    r"\bpercent(?:age)?\b": "%",
    r"\bper ?cent\b": "%",
    r"\bpct\b": "%",
    r"\b%\b": "%",
    r"\bliters?\b": "L",
    r"\bhectares?\b": "ha",
    r"\bsquare\s*meters?\b": "m²",
}

SCALE_MULTIPLIERS = {
    "thousand": 1_000,
    "million": 1_000_000,
    "billion": 1_000_000_000,
}

GALLON_TO_CUBIC_METERS = 0.00378541
BLOCKED_UNITS = {"pledged", "target", "goal", "projects", "initiatives", "plastic"}


def normalize_unit_and_number(raw_value: str, expected_unit: str) -> str:
    """
    Normalizes raw extracted values to expected units.

    Args:
        raw_value (str): Raw extracted string.
        expected_unit (str): Expected standardized unit.

    Returns:
        str: Normalized value or "N/A" if invalid.
    """
    original = raw_value.strip()
    lowered = original.lower()

    if lowered in ["n/a", "", "-", "not available"]:
        return "N/A"

    for pattern, replacement in UNIT_NORMALIZATION.items():
        lowered = re.sub(pattern, replacement, lowered, flags=re.IGNORECASE)

    if expected_unit == "%" and not re.search(r"%", lowered):
        return "N/A"

    if expected_unit == "%" and re.search(r"(million|billion|kwh|mwh|gwh)", lowered):
        return "N/A"

    if any(bad in lowered for bad in BLOCKED_UNITS):
        return "N/A"

    if re.search(r"gallons", lowered):
        multiplier = 1_000_000_000 if "billion" in lowered else 1
        match = re.search(r"([\d.,]+)", lowered)
        if match:
            try:
                num = (
                    float(match.group(1).replace(",", ""))
                    * multiplier
                    * GALLON_TO_CUBIC_METERS
                )
                return f"{round(num, 2)} cubic meters"
            except ValueError:
                return "N/A"

    match = re.search(
        r"([\d.,]+)\s*(thousand|million|billion)?\s*([a-zA-Z°%³]*)", lowered
    )
    if match:
        num_str, scale, unit = match.groups()
        try:
            num = float(num_str.replace(",", ""))
            if scale in SCALE_MULTIPLIERS:
                num *= SCALE_MULTIPLIERS[scale]
            num = round(num, 2)

            for pattern, replacement in UNIT_NORMALIZATION.items():
                if re.fullmatch(pattern, unit.strip(), re.IGNORECASE):
                    return f"{num} {replacement}"
            return f"{num} {expected_unit}"
        except ValueError:
            return "N/A"

    return "N/A"


def extract_numeric(value: str) -> float:
    """
    Extracts numeric value from a string.

    Args:
        value (str): Input value as string.

    Returns:
        float: Extracted numeric value or None if parsing fails.
    """
    try:
        return float(re.sub(r"[^\d.]", "", value.replace(",", "")))
    except ValueError:
        return None


def validate_value(value: str, rules: dict) -> dict:
    """
    Validates a numeric value against defined rules.

    Args:
        value (str): Value to validate.
        rules (dict): Validation rule set with min, max, warn_above keys.

    Returns:
        dict: Validation result containing flags and numeric value.
    """
    num = extract_numeric(value)
    if num is None:
        return {"valid": False, "warning": False, "value": None}
    min_val = rules.get("min", float("-inf"))
    max_val = rules.get("max", float("inf"))
    warn_above = rules.get("warn_above", float("inf"))
    return {
        "valid": min_val <= num <= max_val,
        "warning": num > warn_above,
        "value": num,
    }


def postprocess_value(
    raw_value: str,
    expected_unit: str,
    validation_rules: dict,
    expected_type: str = "float",
    aim: str = "reduction",
) -> dict:
    """
    Postprocesses and validates an extracted CSR indicator value.

    Args:
        raw_value (str): Raw extracted value string.
        expected_unit (str): Expected unit for normalization.
        validation_rules (dict): Validation rules for the value.
        expected_type (str, optional): Expected data type ("float" or "int"). Defaults to "float".
        aim (str, optional): Aim of the indicator ("reduction" or "increase"). Defaults to "reduction".

    Returns:
        dict: Processed result including normalized value, validation status, and warnings.
    """
    if not raw_value or raw_value.strip().lower() in ["n/a", "", "-", "not available"]:
        return {
            "original": raw_value,
            "normalized": "N/A",
            "numeric_value": None,
            "valid": False,
            "warning": False,
        }

    lowered = raw_value.strip().lower()

    if aim == "reduction" and re.search(
        r"(\d+\.?\d*)\s*%\s*(reduction|decrease|improvement)", lowered
    ):
        return {
            "original": raw_value,
            "normalized": "N/A",
            "numeric_value": None,
            "valid": False,
            "warning": False,
        }

    if expected_unit == "%":
        percent_match = re.search(r"(\d+\.?\d*)\s*%", lowered)
        if percent_match:
            percent = float(percent_match.group(1))
            if percent <= 100:
                return {
                    "original": raw_value,
                    "normalized": f"{percent}%",
                    "numeric_value": percent,
                    "valid": True,
                    "warning": False,
                }
            else:
                return {
                    "original": raw_value,
                    "normalized": "N/A",
                    "numeric_value": None,
                    "valid": False,
                    "warning": True,
                }

    normalized = normalize_unit_and_number(raw_value, expected_unit)
    if normalized == "N/A":
        return {
            "original": raw_value,
            "normalized": "N/A",
            "numeric_value": None,
            "valid": False,
            "warning": False,
        }

    numeric_value = (
        extract_numeric(normalized.split()[0]) if normalized != "N/A" else None
    )
    if expected_type == "float" and not isinstance(numeric_value, float):
        return {
            "original": raw_value,
            "normalized": "N/A",
            "numeric_value": None,
            "valid": False,
            "warning": False,
        }

    result = validate_value(normalized, validation_rules)
    return {
        "original": raw_value,
        "normalized": normalized,
        "numeric_value": result["value"],
        "valid": result["valid"],
        "warning": result["warning"],
    }
