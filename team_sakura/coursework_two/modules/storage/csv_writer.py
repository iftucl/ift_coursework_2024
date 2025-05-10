import csv

def save_to_csv(data, csv_path, company_name=None, pdf_link=None):
    """
    Save normalized indicator data to a CSV file with extra metadata.

    Args:
        data (dict): Normalized data dict containing indicators and year.
        csv_path (str): Path to save the CSV file.
        company_name (str, optional): Company name to include in the CSV.
        pdf_link (str, optional): PDF link to include in the CSV.
    """

    # Extract year safely
    year_data = data.get("year", {})
    year = year_data.get("value", None)
    year = int(year) if year is not None else "N/A"

    with open(csv_path, "w", newline="") as file:
        writer = csv.writer(file)

        # Add header with extra metadata
        writer.writerow(["Company Name", company_name or "N/A"])
        writer.writerow(["PDF Link", pdf_link or "N/A"])
        writer.writerow([])  # Empty row
        writer.writerow(["Thematic Area", "Indicator", "Value", "Unit", "Year"])

        # Indicator mapping to thematic areas
        thematic_mapping = {
            "scope_1_emissions": "Greenhouse Gas Emissions",
            "scope_2_emissions": "Greenhouse Gas Emissions",
            "scope_3_emissions": "Greenhouse Gas Emissions",
            "total_water_withdrawal": "Water Usage",
            "total_water_consumption": "Water Usage",
            "total_energy_consumption": "Energy",
            "renewable_energy_consumption": "Energy",
            "total_waste_generated": "Waste & Recycling",
            "hazardous_waste": "Waste & Recycling"
        }

        indicators = list(thematic_mapping.keys())

        # Write indicators
        for indicator in indicators:
            ind_data = data.get(indicator)
            thematic_area = thematic_mapping.get(indicator, "Unknown")

            if ind_data:
                writer.writerow(
                    [thematic_area, indicator.replace("_", " ").title(), ind_data.get("value", ""),
                     ind_data.get("unit", ""), year])
            else:
                writer.writerow([thematic_area, indicator.replace("_", " ").title(), "N/A", "N/A", year])

        # Write targets (if any)
        targets = data.get("targets", [])
        for target in targets:
            writer.writerow(["Future Targets", target.get("target", "N/A"), "", "", target.get("target_year", "")])
