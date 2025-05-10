import re

def has_valid_indicator(data):
    """
    Check if the provided data contains at least one valid indicator.

    A valid indicator is defined as:
    - A dictionary entry with a non-None 'value' field.
    - OR a string that contains at least one numeric character (e.g., digits or percentages).

    Args:
        data (dict): The data dictionary where each value can be a dict or string representing indicator information.

    Returns:
        bool: True if at least one valid indicator exists, False otherwise.
    """
    for v in data.values():
        if isinstance(v, dict):
            # Check if dictionary has a non-None value field
            if v.get("value") is not None:
                return True
        elif isinstance(v, str):
            # Check if the string contains any numeric characters
            if re.search(r'\d', v):
                return True
    return False