import json
import os
import re
import requests
import tiktoken
import fitz  # PyMuPDF
from dotenv import load_dotenv

# Load API key from .env
load_dotenv()
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")

url = "https://api.deepseek.com/v1/chat/completions"
headers = {
    "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
    "Content-Type": "application/json"
}

def get_first_n_tokens(raw_text, n_tokens):
    encoding = tiktoken.get_encoding("cl100k_base")
    tokens = encoding.encode(raw_text)
    return encoding.decode(tokens[:n_tokens])

def extract_metric_keywords(esg_data):
    keywords = []

    def recurse(data):
        if isinstance(data, dict):
            for k, v in data.items():
                if isinstance(v, dict):
                    if any(isinstance(val, (int, float, str)) for val in v.values()):
                        keywords.append(k)
                    recurse(v)

    recurse(esg_data)
    return list(set(keywords))

def extract_relevant_pages(pdf_path, keywords):
    doc = fitz.open(pdf_path)
    relevant_text = ""

    for page in doc:
        text = page.get_text()
        if any(keyword.lower() in text.lower() for keyword in keywords):
            relevant_text += text + "\n"

    return relevant_text

def create_validation_prompt(esg_data, filtered_text, company_name):
    first_tokens = get_first_n_tokens(filtered_text, 7000)
    return f"""
You are an ESG data validator.

You are given:
1. The company name: {company_name}.
2. The filtered ESG report text (only pages with relevant metrics).
3. ESG data extracted from the report (as JSON).

Your task:
- For each metric in the ESG data, assign a validation status based on the text:
  - "validated": "yes" if clearly verified
  - "validated": "no" if not present or unrealistic
  - "validated": "maybe" if uncertain or partially visible

Respond ONLY with the corrected JSON.

--- Company Name ---
{company_name}

--- ESG Report (Filtered Pages) ---
{first_tokens}

--- ESG Data (Extracted Metrics) ---
{json.dumps(esg_data, indent=2)}
""".strip()

def extract_json_from_markdown(text):
    match = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL)
    return match.group(1).strip() if match else text.strip()

def validate_esg_data_with_deepseek(esg_data, company_name, pdf_path):
    try:
        keywords = extract_metric_keywords(esg_data)
        filtered_text = extract_relevant_pages(pdf_path, keywords)
        prompt = create_validation_prompt(esg_data, filtered_text, company_name)

        payload = {
            "model": "deepseek-chat",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3
        }

        response = requests.post(url, headers=headers, json=payload)
        print("Status Code:", response.status_code)

        if response.status_code != 200:
            raise ValueError(f"Error: {response.status_code} - {response.text}")

        raw_content = response.json()["choices"][0]["message"]["content"]
        clean_json_str = extract_json_from_markdown(raw_content)
        return json.loads(clean_json_str)

    except Exception as e:
        raise Exception(f"Validation failed: {e}")

def main():
    company_name = "Nvidia Corporation"
    pdf_path = "filtered_report.pdf"  # Path to the downloaded PDF
    esg_data = {
        "Scope Data": {
            "Scope 1": {"FY24": 14390, "Units": "MT CO₂e", "validated": "maybe"},
            "Scope 2 (market-based)": {"FY24": 40555, "Units": "MT CO₂e"}
        },
        "Energy Data": {
            "Electricity consumption": {"2024": 612008, "Units": "MWh"}
        },
        "Water Data": {
            "water_withdrawal": {"2024": 382636, "Units": "m³"}
        }
    }

    try:
        validated = validate_esg_data_with_deepseek(pdf_path, esg_data, company_name)
        print("✅ Validated ESG Data:")
        print(json.dumps(validated, indent=2))
    except Exception as e:
        print(f"❌ {e}")

if __name__ == "__main__":
    main()
