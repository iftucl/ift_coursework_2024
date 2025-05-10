def validate_water_extraction(val, unit, mcm):
    allowed_units = {
        "cubic meters", "megaliters", "gallons", "liters", "gallons_billion"
    }

    if val is None or unit is None or mcm is None:
        return False
    if unit not in allowed_units:
        return False
    if not isinstance(val, (int, float)) or not isinstance(mcm, (int, float)):
        return False
    if val <= 0 or mcm <= 0:
        return False
    if val > 1_000_000_000:
        return False
    if mcm > 10000 or mcm < 0.01:
        return False
    return True


def validate_donation_extraction(val):
    if val is None:
        return False, "Value is None"
    if not isinstance(val, (int, float)):
        return False, "Value not numeric"
    if val <= 1000:
        return False, "Donation too small"
    if val > 1_000_000_000:
        return False, "Donation unreasonably large"
    return True, None


def validate_waste_extraction(val, unit, mt):
    allowed_units = {
        "metric tons", "tonnes", "tons", "kg", "kilograms"
    }

    # Basic null checks
    if val is None or unit is None or mt is None:
        return False

    # Type checks
    if not isinstance(val, (int, float)) or not isinstance(mt, (int, float)):
        return False

    unit = unit.lower().strip()
    if unit not in allowed_units:
        return False

    # Value sanity bounds
    if val <= 0 or mt <= 0:
        return False
    if val > 10_000_000_000 or mt > 10_000_000 or mt < 0.001:
        return False

    # Heuristic check for conversion
    unit_expected_mt = {
        "kg": val / 1000,
        "kilograms": val / 1000,
        "tons": val * 0.90718474,
        "tonnes": val,
        "metric tons": val,
    }

    estimated = unit_expected_mt.get(unit)
    if estimated:
        # Allow up to 30% relative deviation to account for rounding, scanning errors
        error_ratio = abs(estimated - mt) / max(mt, 1e-6)
        if error_ratio > 0.3:
            return False

    return True


def validate_renewable_energy_extraction(data):
    """
    Validates renewable energy extraction output:
    - Expects a dict with keys 'standardised_mwh' and/or 'percentage'.
    - Amount must be a valid number in expected MWh range.
    - Percentage must be a float between 0 and 100 inclusive.
    """
    if not isinstance(data, dict):
        return False

    amount = data.get("standardised_mwh")
    percentage = data.get("percentage")

    valid_amount = False
    valid_percentage = False

    # Validate amount
    if amount is not None:
        if isinstance(amount, (int, float)) and 0 < amount <= 100_000_000:
            valid_amount = True

    # Validate percentage
    if percentage is not None:
        if isinstance(percentage, (int, float)) and 0 <= percentage <= 100:
            valid_percentage = True

    return valid_amount or valid_percentage


def validate_air_emissions(data):
    """
    Validates air emission metrics (NOx, SOx, VOC) in metric tons.
    - Accepts partial data (e.g., only NOx or SOx).
    - Validates range: 0 ≤ value ≤ 1,000,000
    - Expects at least one pollutant to be valid.
    """
    if not isinstance(data, dict):
        return False

    keys = ["standardised_nox", "standardised_sox", "standardised_voc"]
    valid_count = 0

    for key in keys:
        val = data.get(key)
        if val is None:
            continue
        if isinstance(val, (int, float)) and 0 <= val <= 1_000_000:
            valid_count += 1
        else:
            return False  # Fail fast if a value is invalid

    return valid_count > 0  # Require at least one pollutant to pass

def validate_scope_emissions(data):
    """
    Validates extracted Scope 1, 2, 3, and Total Emissions (in metric tons CO2e).
    - Accepts values as float/int or None.
    - At least one key must be present with a valid value.
    - Valid values: > 0 and ≤ 10 billion metric tons.
    """
    if not isinstance(data, dict):
        return False

    required_keys = ["scope_1", "scope_2", "scope_3", "total_emissions"]
    has_valid_value = False

    for key in required_keys:
        val = data.get(key)
        if val is None:
            continue
        if not isinstance(val, (int, float)):
            return False
        if not (0 < val <= 10_000_000_000):
            return False
        has_valid_value = True

    return has_valid_value