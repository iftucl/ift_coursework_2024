"""
This module processes and standardizes CSR report data by converting indicator units 
to a target unit using a machine learning model (LLM). It interacts with a PostgreSQL 
database to fetch, process, and update the data.

Key functions:
- Fetch rows from the database that need unit standardization.
- Build prompts for the LLM to convert units based on the CSR indicator.
- Call the LLM API to get the conversion results.
- Parse the response and update the database with standardized values.

It uses `psycopg2` for PostgreSQL interaction, `dotenv` for environment variable management, 
`tqdm` for progress tracking, and `concurrent.futures` for concurrent execution of row processing.
"""

import os
import json
import re
import psycopg2
from dotenv import load_dotenv
from tqdm import tqdm
from openai import OpenAI
from concurrent.futures import ThreadPoolExecutor, as_completed

# === Load environment variables ===
env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../.env'))
load_dotenv(dotenv_path=env_path)
api_key = os.getenv("DEEPSEEK_API_KEY")
print("API Key Loaded:", api_key is not None)  # Check if API key loaded successfully

# === Initialize LLM client ===
client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")

# === PostgreSQL configuration ===
db_config = {
    "dbname": "fift",
    "user": "postgres",
    "password": "postgres",
    "host": "host.docker.internal",
    "port": 5439
}

def get_connection():
    """
    Establishes and returns a connection to the PostgreSQL database using the specified configuration.

    :return: psycopg2 connection object
    :rtype: psycopg2.extensions.connection
    """
    return psycopg2.connect(**db_config)

# === Query rows to standardize ===
def fetch_rows_to_standardize(conn):
    """
    Fetches rows from the database that require unit standardization.

    :param conn: The psycopg2 connection object to the database.
    :type conn: psycopg2.extensions.connection
    :return: List of rows containing data to be standardized.
    :rtype: list of tuples
    """
    with conn.cursor() as cur:
        cur.execute(""" 
            SELECT d.data_id, d.indicator_name, d.value_raw, d.unit_raw,
                   i.unit AS target_unit, i.description
            FROM csr_reporting.CSR_Data d
            JOIN csr_reporting.CSR_Indicators i ON d.indicator_id = i.indicator_id
            WHERE i.is_target = FALSE
              AND d.value_raw IS NOT NULL
              AND d.value_standardized IS NULL
        """)
        return cur.fetchall()

# === Prompt builder ===
def build_conversion_prompt(indicator_name, description, value_raw, unit_raw, target_unit):
    """
    Constructs a prompt for the LLM to convert a unit of measurement from the raw value to the target unit.

    :param indicator_name: The name of the CSR indicator.
    :type indicator_name: str
    :param description: The description of the CSR indicator.
    :type description: str
    :param value_raw: The raw value to be converted.
    :type value_raw: str
    :param unit_raw: The unit of the raw value.
    :type unit_raw: str
    :param target_unit: The target unit to convert the value to.
    :type target_unit: str
    :return: The LLM prompt as a formatted string.
    :rtype: str
    """
    return f"""You are an intelligent assistant skilled in converting indicator units from company CSR reports.

The indicator is "{indicator_name}", and its description is: {description}

We have extracted the raw value as: {value_raw}, with the original unit: {unit_raw}. Please convert it to the target unit "{target_unit}".

Please note:
- Output in English only;
- If the units cannot be converted (e.g., "tons" to "%"), set convertibility to FALSE and value_standardized to NULL;
- If conversion is possible, set convertibility to TRUE, and provide the converted value in value_standardized (number only, no unit);
- If the original and target units are the same or nearly identical in meaning, set convertibility to TRUE, and set value_standardized to the same value as raw value;
- Note that value_standardized is a numeric number, and not separated by commas.
- Please only return a structured JSON response in the following format (no prefix/suffix like ```json, and do not include any natural language explanation before or after the JSON.):
{{
  "convertibility": true,
  "value_standardized": "...",
  "note": "..."
}}
"""

# === Call DeepSeek API ===
def call_llm(prompt):
    """
    Sends a request to the LLM (DeepSeek API) to process the unit conversion based on the given prompt.

    :param prompt: The conversion prompt to send to the LLM.
    :type prompt: str
    :return: The response content from the LLM.
    :rtype: str
    """
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": "You are an intelligent assistant skilled in converting indicator units from company CSR reports."},
            {"role": "user", "content": prompt},
        ],
        stream=False,
    )
    return response.choices[0].message.content

# === Clean and parse LLM response ===
def safe_json_parse(response_text):
    """
    Cleans and parses the raw response text from the LLM into a structured JSON format.

    :param response_text: The raw response text from the LLM.
    :type response_text: str
    :return: The parsed JSON object containing the conversion result.
    :rtype: dict
    :raises ValueError: If the response cannot be parsed into valid JSON.
    """
    cleaned = response_text.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    if not cleaned:
        raise ValueError("LLM returned empty response after cleaning")
    return json.loads(cleaned)

# === Update database with conversion results ===
def update_standardized(conn, data_id, value_standardized, unit_standardized, unit_conversion_note=None):
    """
    Updates the database with the standardized value and unit for the given data ID.

    :param conn: The psycopg2 connection object to the database.
    :type conn: psycopg2.extensions.connection
    :param data_id: The ID of the data row to update.
    :type data_id: int
    :param value_standardized: The standardized value to be saved.
    :type value_standardized: str
    :param unit_standardized: The unit of the standardized value.
    :type unit_standardized: str
    :param unit_conversion_note: Additional notes about the unit conversion (optional).
    :type unit_conversion_note: str, optional
    """
    with conn.cursor() as cur:
        cur.execute("""
            UPDATE csr_reporting.CSR_Data
            SET value_standardized = %s,
                unit_standardized = %s,
                unit_conversion = %s
            WHERE data_id = %s
        """, (value_standardized, unit_standardized, unit_conversion_note, data_id))
    conn.commit()

# === Validate if value is a legal number ===
def is_valid_number(value):
    """
    Checks if the given value is a valid numeric value (either integer or float).

    :param value: The value to check.
    :type value: str
    :return: True if the value is valid, otherwise False.
    :rtype: bool
    """
    try:
        float(value)
        return True
    except Exception:
        return False

# === Process a single row ===
def process_row(conn, row):
    """
    Processes a single row of CSR data, including calling the LLM API and updating the database.

    :param conn: The psycopg2 connection object to the database.
    :type conn: psycopg2.extensions.connection
    :param row: A tuple representing the CSR data to process.
    :type row: tuple
    :return: The data ID of the processed row, or None if processing failed.
    :rtype: int or None
    """
    data_id, indicator_name, value_raw, unit_raw, target_unit, description = row

    try:
        # Case 1: Units match
        if unit_raw and target_unit and unit_raw.strip().lower() == target_unit.strip().lower():
            update_standardized(conn, data_id, value_raw, target_unit, "Units are identical, no conversion needed")
            print(f"✅ Data ID {data_id} units match, value standardized directly")
            return data_id

        # Case 2: Use LLM
        prompt = build_conversion_prompt(indicator_name, description, value_raw, unit_raw, target_unit)
        llm_response = call_llm(prompt)
        parsed = safe_json_parse(llm_response)
        can_convert = parsed.get("convertibility", False)
        result_value = parsed.get("value_standardized")
        note = parsed.get("note", "")

        if not can_convert:
            update_standardized(conn, data_id, None, None, note)
            print(f"⚠️ Data ID {data_id} unit not convertible, reason recorded: {note}")
            return None

        if not is_valid_number(result_value):
            raise ValueError(f"Standardized result is not a number: {result_value}")

        update_standardized(conn, data_id, result_value, target_unit, note)
        print(f"✅ Data ID {data_id} conversion successful, standardized value: {result_value}")
        return data_id

    except Exception as e:
        conn.rollback()
        print(f"❌ Data ID {data_id} standardization failed: {e}")

        # Print raw response for debug
        try:
            print(f"🧠 LLM raw response for Data ID {data_id} (exception case):\n{llm_response}")
        except:
            pass

        return None

# === Main function ===
def main():
    """
    Main function to process all pending rows in the database by calling the process_row function concurrently.
    """
    conn = get_connection()
    try:
        rows = fetch_rows_to_standardize(conn)
        print(f"{len(rows)} records need to be standardized")

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(process_row, conn, row) for row in rows]

            for future in tqdm(as_completed(futures), total=len(futures), desc="Standardization Progress"):
                future.result()
    finally:
        conn.close()

if __name__ == "__main__":
    main()
