import os
import json
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
    return psycopg2.connect(**db_config)

# === Query rows to standardize (non-target indicators where value_raw is not null but value_standardized is null) ===
def fetch_rows_to_standardize(conn):
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
    return f"""You are an intelligent assistant skilled in converting indicator units from company CSR reports.

The indicator is "{indicator_name}", and its description is: {description}

We have extracted the raw value as: {value_raw}, with the original unit: {unit_raw}. Please convert it to the target unit "{target_unit}".

Please note:
- Output in English only;
- If the units cannot be converted (e.g., "tons" to "%"), set convertibility to FALSE and value_standardized to NULL;
- If conversion is possible, set convertibility to TRUE, and provide the converted value in value_standardized (number only, no unit);
- If the original and target units are the same or nearly identical in meaning, set convertibility to TRUE and value_standardized to the original value;
- Please return a structured JSON response in the following format (no prefix/suffix like ```json):
{{
  "convertibility": true,
  "value_standardized": "...",
  "note": "..."
}}
"""

# === Call DeepSeek API ===
def call_llm(prompt):
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": "You are an intelligent assistant skilled in converting indicator units from company CSR reports."},
            {"role": "user", "content": prompt},
        ],
        stream=False,
    )
    return response.choices[0].message.content

# === Update database with conversion results (including unit_conversion note) ===
def update_standardized(conn, data_id, value_standardized, unit_standardized, unit_conversion_note=None):
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
    try:
        float(value)
        return True
    except Exception:
        return False

# === Process a single row ===
def process_row(conn, row):
    data_id, indicator_name, value_raw, unit_raw, target_unit, description = row

    try:
        # Case 1: Units match, directly store the original value
        if unit_raw and target_unit and unit_raw.strip().lower() == target_unit.strip().lower():
            update_standardized(conn, data_id, value_raw, target_unit, "Units are identical, no conversion needed")
            print(f"✅ Data ID {data_id} units match, value standardized directly")
            return data_id

        # Case 2: Use LLM to determine convertibility
        prompt = build_conversion_prompt(indicator_name, description, value_raw, unit_raw, target_unit)
        llm_response = call_llm(prompt)
        parsed = json.loads(llm_response)

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
        return None

# === Main function ===
def main():
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
