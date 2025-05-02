def standardize_unit_value(value, unit):
    """
    Normalize units to base units and convert value accordingly.
    Returns (normalized_value, normalized_unit)
    """
    if value is None or unit is None:
        return value, unit

    unit_key = unit.lower().strip()

    # Units to REMOVE (invalid or reporting only)
    INVALID_UNITS = ["usd", "eur", "gbp", "currency", "reporting currency"]

    if unit_key in INVALID_UNITS:
        return None, None

    UNIT_CONVERSION = {
        # Mass / Emissions / Waste
        "metric tonnes": ("tons", 1),
        "metric tons": ("tons", 1),
        "metric tons co2e": ("tons", 1),
        "tonnes": ("tons", 1),
        "mt co2e": ("tons", 1),
        "kilotons": ("tons", 1000),
        "kt": ("tons", 1000),
        "kg": ("tons", 0.001),
        "kilograms": ("tons", 0.001),
        "cubic yards": ("cubic meters", 0.7645549),
        "cubic yards (cy)": ("cubic meters", 0.7645549),

        # Energy
        "mwh": ("kwh", 1000),
        "gwh": ("kwh", 1000000),
        "gigajoules": ("kwh", 277.778),
        "mmbtu": ("kwh", 293.071),
        "kilowatt-hours": ("kwh", 1),
        "kilowatt hours": ("kwh", 1),
        "kilowatt hour": ("kwh", 1),

        # Water
        "thousand cubic meters (m3)": ("cubic meters", 1000),
        "thousand cubic meters": ("cubic meters", 1000),
        "cubic meters": ("liters", 1000),  # convert all cubic meters to liters
        "kilolitres": ("liters", 1000),
    }

    if unit_key in UNIT_CONVERSION:
        target_unit, factor = UNIT_CONVERSION[unit_key]
        return value * factor, target_unit

    # fallback - no conversion
    return value, unit
