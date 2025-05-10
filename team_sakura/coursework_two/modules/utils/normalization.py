import re

def normalize_indicator_value(raw_text):
    """
    Normalize raw indicator text into a structured dictionary with numeric value and unit.

    This function handles different formats such as:
    - Percentage values (e.g., "27%")
    - Numeric values with units (e.g., "123,456 metric tons CO2-e")
    - Plain numeric strings
    - Non-reported or unavailable values (e.g., "N/A", "Not reported", "-")

    Args:
        raw_text (str or any): The raw indicator value extracted from a source.

    Returns:
        dict: A dictionary containing:
            - 'value': The numeric value (float, int, or None)
            - 'unit': The unit of measurement (str or None)
    """


    if raw_text is None:
        return {"value": None, "unit": None}

    # Ensure raw_text is string
    if not isinstance(raw_text, str):
        raw_text = str(raw_text)

    if raw_text in ["N/A", "Not reported", "-", ""]:
        return {"value": None, "unit": None}

    raw_text = raw_text.strip()

    # Percentage
    if raw_text.endswith("%"):
        try:
            return {"value": float(raw_text.strip('%')), "unit": "%"}
        except ValueError:
            return {"value": None, "unit": "%"}

    # Number + Unit
    match = re.match(r"([\d,\.]+)\s*(.*)", raw_text)
    if match:
        num_part = match.group(1).replace(",", "")
        unit_part = match.group(2).strip() or None
        try:
            num_value = float(num_part) if '.' in num_part else int(num_part)
            return {"value": num_value, "unit": unit_part}
        except ValueError:
            return {"value": None, "unit": unit_part}

    # If only numeric string
    if raw_text.isdigit():
        return {"value": int(raw_text), "unit": None}

    return {"value": None, "unit": None}

    # If only numeric
    if raw_text.isdigit():
        return {"value": int(raw_text), "unit": None}

    return {"value": None, "unit": None}


def normalize_key(key: str) -> str:
    return key.strip().lower().replace(" ", "_")