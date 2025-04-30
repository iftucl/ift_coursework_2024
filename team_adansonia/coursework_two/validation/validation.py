import json
import os
import re
from dotenv import load_dotenv
from loguru import logger
from team_adansonia.coursework_two.validation.deepseek_validation import validate_esg_data_with_deepseek
from team_adansonia.coursework_two.validation.deepseek_validation_2 import validate_esg_data_with_deepseek

#TODO: If number is not on the same page with metric, do not validate
#TODO: Standardise years
#TODO: LLM for validation? Append validation status for each data point


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

def validate_and_clean_data(raw_data: dict, filtered_text: str):
    """
    Cleans and validates raw ESG data by verifying the values and units, ensuring they conform to expected formats
    and lie within predefined ranges. This function also checks if the value appears in the filtered ESG report text.

    Parameters:
    - raw_data (dict): The raw ESG data to be validated and cleaned, typically structured by categories and metrics.
    - filtered_text (str): The filtered text from the ESG report used to check if values appear in the report.

    Returns:
    - cleaned (dict): A dictionary containing cleaned and validated ESG data with issues removed.
    - issues (list): A list of dictionaries detailing any issues found during the validation process, including missing values,
      unrecognized units, and mismatches between the raw data and filtered text.

    """
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
                issues.append({
                    "category": category,
                    "metric": metric,
                    "issue": "Metric is None"
                })
                continue

            cleaned[category][metric] = {}
            units = None

            for year, pair in yearly_data.items():
                if not isinstance(pair, list) or len(pair) != 2:
                    continue

                value, unit = pair

                if value is None or unit is None:
                    logger.warning(f"Skipping {metric} for {year} due to missing value or unit.")
                    issues.append({
                        "category": category,
                        "metric": metric,
                        "year": year,
                        "issue": "Missing value or unit"
                    })
                    continue

                logger.debug(f"Processing value: {value}, unit: {unit} for metric: {metric}, year: {year}")

                normalized_unit = unit.strip().lower()
                base_value = None
                matched = False

                # Check if value appears in filtered text
                if str(int(value)) not in filtered_text and str(float(value)) not in filtered_text:
                    issues.append({
                        "category": category,
                        "metric": metric,
                        "year": year,
                        "issue": f"Value {value} not found in raw filtered text"
                    })

                for pattern, scale in unit_patterns:
                    if re.search(pattern, normalized_unit):
                        matched = True
                        base_value = value * scale

                        if min_base is not None and max_base is not None:
                            if not (min_base <= base_value <= max_base):
                                issues.append({
                                    "category": category,
                                    "metric": metric,
                                    "year": year,
                                    "issue": f"Out of range: {base_value} (expected {min_base}-{max_base})"
                                })

                        cleaned[category][metric][year] = value
                        if units is None:
                            units = unit
                        break

                if not matched:
                    cleaned[category][metric][year] = value
                    if units is None:
                        units = unit
                    issues.append({
                        "category": category,
                        "metric": metric,
                        "year": year,
                        "issue": f"Unrecognized unit: '{unit}'"
                    })

            # Attach unit label after processing all years
            if units:
                cleaned[category][metric]["Units"] = units

            # Remove metric if it contains no valid data (except maybe Units)
            if not any(k for k in cleaned[category][metric] if k.lower() != "units"):
                cleaned[category].pop(metric)

        # Remove category if it's completely empty
        if not cleaned[category]:
            cleaned.pop(category)

    print(json.dumps(cleaned, indent=2))
    return cleaned, issues


def full_validation_pipeline(parsed_data, filtered_text, company_name, pdf_path):
    """
     Runs the full validation pipeline for ESG data by first performing internal validation, and then using OpenAI
     for further validation. If OpenAI validation fails, it falls back to using the internally validated data.

     Parameters:
     - parsed_data (dict): The raw ESG data that needs validation.
     - filtered_text (str): The filtered text from the ESG report used to verify the data.
     - company_name (str): The name of the company to help contextualize the validation.

     Returns:
     - corrected_data (dict): The validated ESG data, which may have been further corrected by OpenAI.

     """
    print("🔍 Step 1: Running internal validation...")
    cleaned_data, internal_issues = validate_and_clean_data(parsed_data, filtered_text)

    try:
        print("🤖 Step 2: Validating with DeepSeek...")
        corrected_data = validate_esg_data_with_deepseek(cleaned_data, company_name, pdf_path)
        print("\n✅ Corrected Data (DeepSeek validation):")
        print(json.dumps(corrected_data, indent=2))
        return corrected_data

    except Exception as e:
        print(f"❌ OpenAI validation failed: {e}")
        print("🔁 Falling back to internally cleaned data.")
        print(json.dumps(cleaned_data, indent=2))
        return cleaned_data
