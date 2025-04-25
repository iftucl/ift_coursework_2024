import json
import os

import tiktoken
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables for OpenAI API key
load_dotenv()

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


# Function to get the first 'n' tokens from the raw text using tiktoken tokenizer
def get_first_n_tokens(raw_text, n_tokens):
    """
    Extracts the first 'n' tokens from raw text using tiktoken tokenizer.
    Uses 'cl100k_base' encoding, which works for GPT models.
    """
    encoding = tiktoken.get_encoding("cl100k_base")
    tokens = encoding.encode(raw_text)
    return str(encoding.decode(tokens[:n_tokens]))




# Function to create prompt for OpenAI validation task
def create_validation_prompt(esg_data, filtered_text, company_name, ):
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
  - If the metric or unit is uncertain or not mentioned because the text was cut of but seems realistic, mark it as "validated": "maybe".

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

    return prompt


# Function to validate ESG data using OpenAI
def validate_esg_data_with_openai(company_name, filtered_text, esg_data):
    prompt = create_validation_prompt(company_name, filtered_text, esg_data)

    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
        )

        # Extract and return validated ESG data
        content = response.choices[0].message.content.strip()
        if not content:
            raise ValueError("Empty response from OpenAI")

        # Return the validated ESG data in JSON format
        return json.loads(content)

    except Exception as e:
        raise Exception(f"Error validating ESG data: {e}")

