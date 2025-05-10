import re


def extract_year(year_string):
    """
    Extract year from a string. Supports formats:
    - 2023
    - FY23 / FY 23 / FY-23
    - 2023-2024 / 2023/2024 → picks latest year
    - Suffix or prefix punctuation (e.g. -2023-, _2023_, 2023.pdf)

    Returns integer year or None.
    """
    year_string = str(year_string)

    # Case 1: Year range (e.g. 2022-2023 or 2022/2023)
    match = re.findall(r'(20\d{2})[\/\-](20\d{2})', year_string)
    if match:
        # Take the higher year
        years = [int(y) for y in match[0]]
        return min(years)

    # Case 2: Direct 4-digit year (looser boundaries, allow _ or - or .)
    match = re.search(r'(?:^|[^0-9])(20\d{2})(?:[^0-9]|$)', year_string)
    if match:
        return int(match.group(1))

    # Case 3: FY followed by 2-digit year (e.g. FY23, FY 23, FY-23)
    match = re.search(r'\bFY[\s\-]?(?P<yy>\d{2})\b', year_string, re.IGNORECASE)
    if match:
        yy = int(match.group("yy"))
        return 2000 + yy

    return None
