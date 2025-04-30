import json
import os
import re
import requests
import tiktoken
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")

# API configuration
url = "https://api.deepseek.com/v1/chat/completions"
headers = {
    "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
    "Content-Type": "application/json"
}


def get_first_n_tokens(raw_text, n_tokens):
    """
    Extract the first `n_tokens` from a given text using the tiktoken tokenizer.

    Args:
        raw_text (str): Full raw text from an ESG report.
        n_tokens (int): Number of tokens to extract.

    Returns:
        str: Truncated string consisting of the first `n_tokens` tokens.
    """
    encoding = tiktoken.get_encoding("cl100k_base")
    tokens = encoding.encode(raw_text)
    return encoding.decode(tokens[:n_tokens])


def create_validation_prompt(esg_data, filtered_text, company_name):
    """
    Create a structured prompt for the Deepseek API to validate ESG data.

    Args:
        esg_data (dict): ESG metrics extracted from a report.
        filtered_text (str): Cleaned text content from the ESG report.
        company_name (str): Name of the company for contextual grounding.

    Returns:
        str: Formatted prompt to be sent to the LLM.
    """
    first_tokens = get_first_n_tokens(filtered_text, 7000)
    prompt = f"""
You are an ESG data validator.

You are given:
1. The company name: {company_name}.
2. The first 10,000 tokens of the filtered ESG report text.
3. ESG data extracted from the report (as JSON).

Your task:
- For each metric in the ESG data, assign a validation status based on the provided text:
  - If the metric or related unit is clearly verified in the text (i.e., it matches or is explicitly mentioned), mark it as "validated": "yes".
  - If the metric or unit is clearly not mentioned or doesn't seem realistic based on the text, mark it as "validated": "no".
  - If the metric or unit is uncertain or not mentioned because the text was cut off but seems realistic, mark it as "validated": "maybe".

IMPORTANT:
- Do not add explanations. Only provide the corrected JSON with the validation status.
- Maintain the original structure of the ESG data.
- Use the company name to help you identify if the metric is realistic or relevant for the company.

--- Company Name ---
{company_name}

--- Filtered Text (First 10,000 Tokens) ---
{first_tokens}

--- ESG Data (Extracted Metrics) ---
{json.dumps(esg_data, indent=2)}
"""
    return prompt.strip()


def extract_json_from_markdown(text):
    """
    Extract JSON from markdown-formatted code block returned by the model.

    Args:
        text (str): Full text content from the model output.

    Returns:
        str: Clean JSON string for parsing.
    """
    match = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL)
    return match.group(1).strip() if match else text.strip()


def validate_esg_data_with_deepseek(esg_data, filtered_text, company_name):
    """
    Send ESG data and report content to Deepseek for validation and parse the returned results.

    Args:
        company_name (str): The name of the company whose ESG data is being validated.
        filtered_text (str): Cleaned ESG report text for validation.
        esg_data (dict): Extracted ESG data to be validated.

    Returns:
        dict: Validated ESG data with updated validation status.

    Raises:
        Exception: If the API response is invalid or fails.
    """
    try:
        prompt = create_validation_prompt(esg_data, filtered_text, company_name)

        payload = {
            "model": "deepseek-chat",
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.3
        }

        response = requests.post(url, headers=headers, json=payload)
        print("Status Code:", response.status_code)
        print("Raw Response Text:", response.text)

        if response.status_code != 200:
            raise ValueError(f"Error from Deepseek: {response.status_code} - {response.text}")

        raw_content = response.json()["choices"][0]["message"]["content"]
        clean_json_str = extract_json_from_markdown(raw_content)
        return json.loads(clean_json_str)

    except Exception as e:
        raise Exception(f"Failed to validate ESG data with Deepseek: {e}")


def main():
    """
    Run a sample ESG validation using sample input.
    This is a test/demo for the validation pipeline.
    """
    company_name = "Example Corp"
    filtered_text = """
    This is a filtered portion of an ESG report.
    It discusses various environmental metrics, energy usage, and sustainability goals.
    """
    esg_data = {
        "energy_usage": {
            "metric": "energy_usage",
            "value": "150 MWh",
            "unit": "MWh",
            "validated": "maybe"
        },
        "water_usage": {
            "metric": "water_usage",
            "value": "5000 gallons",
            "unit": "gallons",
            "validated": "maybe"
        }
    }

    try:
        validated = validate_esg_data_with_deepseek(company_name, filtered_text, esg_data)
        print("✅ Validated ESG Data:")
        print(json.dumps(validated, indent=2))
    except Exception as e:
        print(f"❌ Validation failed: {e}")


if __name__ == "__main__":
    main()
