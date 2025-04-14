import os
import psycopg2
import json
from dotenv import load_dotenv
from datetime import datetime
from openai import OpenAI
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm

# === Load Environment Variables ===
env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../.env'))
load_dotenv(dotenv_path=env_path)
api_key = os.getenv("DEEPSEEK_API_KEY")
print("API Key Loaded:", api_key is not None)

# === Initialize LLM Client ===
client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")

# === PostgreSQL Configuration ===
db_config = {
    "dbname": "fift",
    "user": "postgres",
    "password": "postgres",
    "host": "host.docker.internal",
    "port": 5439
}

def get_connection():
    return psycopg2.connect(**db_config)

def fetch_pending_rows(conn):
    with conn.cursor() as cur:
        cur.execute("""
            SELECT d.data_id, d.indicator_name, d.source_excerpt, d.indicator_id, d.report_year, 
                   i.description, i.is_target
            FROM csr_reporting.CSR_Data d
            JOIN csr_reporting.CSR_indicators i ON d.indicator_id = i.indicator_id
            WHERE d.value_raw IS NULL
        """)
        return cur.fetchall()

# === Prompt Builder ===
def build_prompt(indicator_name, description, is_target, source_excerpt, report_year):
    formatted_paragraphs = "\n".join(
        f"(Page {item['page']}): {item['text']}" for item in source_excerpt
    )

    if is_target:
        return f"""You are an intelligent assistant specialized in extracting indicator data from company CSR reports. Please help identify information related to corporate sustainability *goals*.

From the following paragraphs, extract all goal-oriented statements related to the indicator “{indicator_name}”. These statements typically include plans, commitments, strategic objectives, long-term visions, etc. Extract the original sentences as the raw value for the indicator.

Indicator description: {description}

The following are the matched paragraphs in the report (report year: {report_year}):
{formatted_paragraphs}

Please return only the original goal-related sentences (multiple sentences allowed), along with the relevant page numbers. Output in English only. Return in the following format (do not include anything else such as ```json or other prefixes/suffixes, here's an example output):
{{ "value": "...", "pages": ["page1", "page2"] }}
Where "value" contains the original goal-related text, and "pages" is a list of pages where the goal appears.
"""

    else:
        return f"""You are an intelligent assistant specialized in extracting indicator data from company CSR reports.

From the following paragraphs, extract the numeric value (such as percentage, quantity, amount, etc.) and its unit related to “{indicator_name}”. The indicator description is: {description}

Pay special attention to the following:
- Output in English only;
- Only extract data related to the year {report_year};
- Ensure consistency between value and unit;
- Return plain numeric values, without comma separators;
- If the unit is not explicitly stated but can be inferred from context (e.g., "%", "tons"), include it as well (when unit is %, it should be in the "unit" field, not attached to the number).

The following are the matched paragraphs in the report (report year: {report_year}):
{formatted_paragraphs}

Return the structured result in the format below (do not include anything else such as ```json or other wrappers, here's an example output):
{{
  "value": "55.3",
  "unit": "%",
  "note": "This value represents the actual renewable energy usage rate in {report_year}.",
  "pages": ["page1", "page2"]
}}
"""

# === Call DeepSeek API ===
def call_llm(prompt):
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[ 
            {"role": "system", "content": "You are an intelligent assistant specialized in extracting indicator data from company CSR reports."},
            {"role": "user", "content": prompt},
        ],
        stream=False
    )
    return response.choices[0].message.content

def update_result(conn, data_id, value_raw, unit_raw, llm_response_raw, pdf_page):
    with conn.cursor() as cur:
        cur.execute("""
            UPDATE csr_reporting.CSR_Data
            SET value_raw = %s,
                unit_raw = %s,
                llm_response_raw = %s,
                pdf_page = %s
            WHERE data_id = %s
        """, (value_raw, unit_raw, llm_response_raw, pdf_page, data_id))
    conn.commit()

def is_valid_number(value):
    try:
        float(value)
        return True
    except ValueError:
        return False

def process_row(conn, row):
    data_id, indicator_name, source_excerpt, indicator_id, report_year, description, is_target = row

    try:
        pdf_pages = [str(item['page']) for item in source_excerpt]
        prompt = build_prompt(indicator_name, description, is_target, source_excerpt, report_year)
        llm_output = call_llm(prompt)
        llm_response_raw = llm_output.strip()

        if is_target:
            try:
                if isinstance(llm_output, str):
                    parsed = json.loads(llm_output)
                    value_raw = parsed.get("value")
                else:
                    value_raw = llm_output.strip()
            except json.JSONDecodeError:
                value_raw = llm_output.strip()
            unit_raw = None
        else:
            parsed = json.loads(llm_output)
            value_raw = parsed.get("value")
            unit_raw = parsed.get("unit")

            if value_raw and not is_valid_number(value_raw):
                raise ValueError(f"Invalid numeric value: {value_raw}")

        update_result(conn, data_id, value_raw, unit_raw, llm_response_raw, ",".join(pdf_pages))
        return data_id

    except Exception as e:
        conn.rollback()
        print(f"❌ Failed to process data ID {data_id}: {e}")
        raise

def main():
    conn = get_connection()
    try:
        rows = fetch_pending_rows(conn)
        print(f"Total records to process: {len(rows)}")
        
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(process_row, conn, row) for row in rows]
            for future in tqdm(as_completed(futures), total=len(futures), desc="Processing Progress"):
                try:
                    future.result()
                    print("✅ Successfully processed")
                except Exception as e:
                    print(f"❌ Processing failed: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    main()
