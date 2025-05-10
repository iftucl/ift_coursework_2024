import json
import csv
from pathlib import Path
from typing import Union, List, Dict, Any

def convert_json_to_csv(json_path: Path, csv_path: Path) -> bool:
    """Converts the standardized JSON data (new format) to a flat CSV file.

    Handles both 'reported_indicator' and 'commitment' types.
    Flattens multi-year 'reported_indicator' entries into separate rows.
    """
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"Error: Input JSON file not found at {json_path}")
        return False
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON file {json_path}: {e}")
        return False
    except Exception as e:
        print(f"An unexpected error occurred reading {json_path}: {e}")
        return False

    # Define the comprehensive header for the CSV
    header = [
        "theme", "indicator_name", "type", 
        "years", "values_numeric", "values_text", "unit",  # Primarily for reported_indicator
        "goal_text", "progress_text", "target_value", "target_unit", "baseline_year", "target_year", # Primarily for commitment
        "page_number", "source"
    ]
    
    rows = []

    # Iterate through each theme (top-level key)
    for theme, items in data.items():
        if not isinstance(items, list):
            print(f"Warning: Skipping theme '{theme}' as its value is not a list.")
            continue
            
        # Iterate through each item (indicator or commitment) within the theme
        for item in items:
            if not isinstance(item, dict):
                 print(f"Warning: Skipping invalid item in theme '{theme}': {item}")
                 continue 

            # Determine item type (heuristic: check for 'goal_text')
            is_commitment = "goal_text" in item
            item_type = "commitment" if is_commitment else "reported_indicator"

            # Extract shared fields
            page_nums = item.get("page_number", [])
            page_numbers_str = "; ".join(map(str, page_nums if isinstance(page_nums, list) else [page_nums] if page_nums else []))
            source = item.get("source")
            indicator_name = item.get("indicator_name")

            # --- Handle Commitments --- 
            if is_commitment:
                row = {
                    "theme": theme,
                    "indicator_name": indicator_name,
                    "type": item_type,
                    "years": None,
                    "values_numeric": None,
                    "values_text": None,
                    "unit": None, 
                    "goal_text": item.get("goal_text"),
                    "progress_text": item.get("progress_text"),
                    "target_value": item.get("target_value"),
                    "target_unit": item.get("target_unit"),
                    "baseline_year": item.get("baseline_year"),
                    "target_year": item.get("target_year"),
                    "page_number": page_numbers_str,
                    "source": source,
                }
                rows.append(row)
            
            # --- Handle Reported Indicators --- 
            else: 
                years = item.get("years")
                values_num = item.get("values_numeric")
                values_txt = item.get("values_text")
                unit = item.get("unit")

                # Prepare base data for potentially multiple rows (one per year)
                base_row_data = {
                    "theme": theme,
                    "indicator_name": indicator_name,
                    "type": item_type,
                    "unit": unit,
                    "goal_text": None,
                    "progress_text": None,
                    "target_value": None,
                    "target_unit": None,
                    "baseline_year": item.get("baseline_year"), # Note: schema says null for reported_indicator
                    "target_year": item.get("target_year"),     # Note: schema says null for reported_indicator
                    "page_number": page_numbers_str,
                    "source": source,
                }

                # Normalize years/values into lists for iteration
                year_list = years if isinstance(years, list) else [years]
                val_num_list = values_num if isinstance(values_num, list) else [values_num] * len(year_list)
                val_txt_list = values_txt if isinstance(values_txt, list) else [values_txt] * len(year_list)
                
                # Ensure list lengths match years if years was a list
                if isinstance(years, list) and len(year_list) > 0: 
                    if len(val_num_list) != len(year_list):
                        print(f"Warning ('{indicator_name}'): Adjusting values_numeric length ({len(val_num_list)}) to match years length ({len(year_list)}).")
                        val_num_list = (val_num_list + [None] * len(year_list))[:len(year_list)]
                    if len(val_txt_list) != len(year_list):
                        print(f"Warning ('{indicator_name}'): Adjusting values_text length ({len(val_txt_list)}) to match years length ({len(year_list)}).")
                        val_txt_list = (val_txt_list + [None] * len(year_list))[:len(year_list)]
                elif len(year_list) == 0: # Handle case where years might be empty list
                    year_list = [None]
                    val_num_list = [values_num] if not isinstance(values_num, list) else [None] # Take first if list, else the value
                    val_txt_list = [values_txt] if not isinstance(values_txt, list) else [None]

                # Create a row for each year
                for i, year in enumerate(year_list):
                    row = base_row_data.copy()
                    current_val_num = val_num_list[i] if i < len(val_num_list) else None
                    current_val_txt = val_txt_list[i] if i < len(val_txt_list) else None
                    
                    row["years"] = int(year) if isinstance(year, (int, float)) else year # Keep string years as is? or null?
                    row["values_numeric"] = current_val_num if isinstance(current_val_num, (int, float)) else None
                    row["values_text"] = str(current_val_txt) if current_val_txt is not None and row["values_numeric"] is None else None # Use text only if numeric is null
                    
                    rows.append(row)

    # Write to CSV
    if not rows:
        print("Warning: No data rows were generated. CSV file will be empty or contain only headers.")

    try:
        csv_path.parent.mkdir(parents=True, exist_ok=True)
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=header, extrasaction='ignore') # Ignore extra fields not in header
            writer.writeheader()
            writer.writerows(rows)
        print(f"Successfully converted JSON to CSV: {csv_path}")
        return True
    except IOError as e:
        print(f"Error writing CSV file to {csv_path}: {e}")
        return False
    except Exception as e:
        print(f"An unexpected error occurred during CSV writing: {e}")
        return False
