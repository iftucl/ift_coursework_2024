"""
This script processes CSR indicator data from multiple CSV files.
It performs the following steps:
    - Concatenates two sets of scraped CSR indicator data.
    - Cleans the report year column.
    - Cleans and standardizes renewable energy usage values.
    - Removes outliers and handles units for several CSR indicators.
    - Renames columns to include unit information.
    - Processes fractional columns (e.g., percentages) and removes values > 100.
    - Removes duplicate and invalid rows.
    - Saves the cleaned CSR indicators to a CSV file.
    - Standardizes company names by matching them with a standard company list,
      using fuzzy matching with a configurable threshold.
    - Saves the final standardized company indicators to a CSV file.
"""

import re

import pandas as pd
from fuzzywuzzy import process

# Since the web scraping was completed in two rounds, the results from both are concatenated here
csr_indicators1 = pd.read_csv("logs/final_output_old.csv")
csr_indicators2 = pd.read_csv("logs/final_output.csv")
csr_indicators = pd.concat([csr_indicators1, csr_indicators2], ignore_index=True)


# Data dealing
csr_indicators["Report Year"] = (
    csr_indicators["Report Year"].astype(str).str.extract(r"(\d{4})")
)
csr_indicators = csr_indicators.dropna(subset=["Report Year"])
csr_indicators["Report Year"] = csr_indicators["Report Year"].astype(int)


def clean_energy_value(x):
    """
    Clean and standardize an energy usage value.

    Attempts to convert a string representing energy usage to a standardized format with "MWh" as the unit.
    If the value is expressed in GWh or TWh, it is converted into MWh.

    Args:
        x: A value (string or numeric) representing the energy usage.

    Returns:
        A string in the format "[numeric value] MWh". If conversion fails, returns an empty string.
    """
    try:
        if pd.isna(x):
            return ""
        x_str = str(x).strip().upper()

        # If it is already in the standard format, just return it directly.
        if x_str.endswith("MWH") and all(
            c.isdigit() or c == "." or c == " "
            for c in x_str.replace("MWH", "").strip()
        ):
            return x  # Or return x_str.title() to standardize the casing.
        if "GWH" in x_str:
            num = float(x_str.replace("GWH", "").strip()) * 1000
        elif "TWH" in x_str:
            num = float(x_str.replace("TWH", "").strip()) * 1_000_000
        else:
            num = float(x_str)
        return f"{int(num)} MWh" if num.is_integer() else f"{round(num, 2)} MWh"
    except Exception as e:
        print(f"cleaning failed: {x} → {e}")
        return ""


csr_indicators["Renewable Energy Usage"] = csr_indicators[
    "Renewable Energy Usage"
].apply(clean_energy_value)


# Remove outliers and handle units
# Define the units to be retained
valid_units = {
    "Annual Carbon Emissions": "tonnes CO₂",
    "Annual Water Consumption": "cubic meters",
    "Renewable Energy Usage": "MWh",
    "Sustainable Materials Usage Ratio": "percent",
    "Waste Recycling Rate": "percent",
}


# Cleaning function: keep data with valid units, remove the units, and set invalid entries to empty
def clean_and_strip_unit(cell, valid_unit):
    """
    Clean a cell value by extracting the numeric component if the specified valid unit is present.

    Args:
        cell: The cell value to process.
        valid_unit: The unit that the cell value should contain.

    Returns:
        The numeric part of the cell as a string if the unit is present; otherwise, an empty string.
    """
    if pd.isna(cell):
        return ""
    cell = str(cell)
    if valid_unit in cell:
        # Extract the numeric part (including integers and decimals)
        match = re.search(r"[\d,.Ee+-]+", cell)
        return match.group(0) if match else ""
    return ""


# Iterate through each column to process the data.
renamed_columns = {}
for col, unit in valid_units.items():
    if col in csr_indicators.columns:
        csr_indicators[col] = csr_indicators[col].apply(
            lambda x: clean_and_strip_unit(x, unit)
        )
        renamed_columns[col] = f"{col} ({unit})"

# Rename columns.
csr_indicators = csr_indicators.rename(columns=renamed_columns)


# Handle fractions.
columns_to_process = [
    "Sustainable Materials Usage Ratio (percent)",
    "Waste Recycling Rate (percent)",
]

for col in columns_to_process:
    # Convert to numeric (set to NaN if conversion fails).
    csr_indicators[col] = pd.to_numeric(csr_indicators[col], errors="coerce")

    # Remove values greater than 100 (set them to blank).
    csr_indicators.loc[csr_indicators[col] > 100, col] = None

csr_indicators = csr_indicators.dropna(subset=["Company Name", "Report Year"])
csr_indicators = csr_indicators.drop_duplicates(subset=["Company Name", "Report Year"])


# save new file
csr_indicators.to_csv("csr_indicators.csv", index=False)


# standardize company name
standard_df = pd.read_csv("company_information.csv")  # Standard company list.
messy_df = pd.read_csv("csr_indicators.csv")  # Messy company list.

# Assume the company name columns in the two tables are as follows.
standard_names = standard_df["security"].tolist()
messy_names = messy_df["Company Name"].tolist()


# Define a function to find the best matching standard name.
def match_company(name, choices, threshold=80):
    """
    Match a company name to a list of standard names using fuzzy string matching.

    Uses fuzzywuzzy's extractOne function to find the best match. If the score is above the threshold,
    the best match is returned; otherwise, None is returned.

    Args:
        name: The company name to match.
        choices: A list of standard company names.
        threshold: An integer threshold for a valid match (default is 80).

    Returns:
        A matched company name if the similarity score exceeds the threshold; otherwise, None.
    """
    match, score = process.extractOne(name, choices)
    if score >= threshold:
        return match
    else:
        return (
            None  # If the similarity is too low, it means no suitable match was found.
        )


# Apply matching on the messy company list.
messy_df["matched_company_name"] = messy_df["Company Name"].apply(
    lambda x: match_company(x, standard_names)
)
messy_df["Company Name"] = messy_df["matched_company_name"]
messy_df = messy_df.drop(columns=["matched_company_name"])
messy_df = messy_df.dropna(subset=["Company Name", "Report Year"])
messy_df.drop_duplicates(subset=["Company Name", "Report Year"], inplace=True)


# Save the results to a new CSV file.
messy_df.to_csv("company_indicators.csv", index=False)

print(
    "Company name standardization completed. Results saved in company_indicators.csv."
)
