import os
import re

from PyPDF2 import PdfReader
from dotenv import load_dotenv
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv(override=True)
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
"""
This module provides tools to extract emissions and sustainability goal information
from corporate PDF reports using PyPDF2 and DeepSeek language models.

Functions include:
- Extracting emissions and goals data by page or paragraph
- Formatting emissions data units
- Summarizing goals and emissions via DeepSeek API
"""
# Extract emmision data text from pdf
def extract_emissions_data_by_page(pdf_path):
    """
    Extracts emissions-related pages from a PDF based on keyword and year matching.

    Args:
        pdf_path (str): Path to the PDF file.

    Returns:
        str: Extracted text containing emissions-related content.
    """
    try:
        reader = PdfReader(pdf_path)
        text = ""
        keywords = ["scope 1", "scope 2", "scope 3", "scope1", "scope2", "scope3"]
        YEAR_PATTERN = re.compile(r"\b(?:FY\s?\d{2,4}|\b20[1-3][0-9]\b)", re.IGNORECASE)

        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                lower_text = page_text.lower()
                if any(kw in lower_text for kw in keywords):
                    text += f"\n--- Page ---\n{page_text}\n"

        return text

    except Exception as e:
        print(f"Error processing PDF: {pdf_path}")
        print(f"Error message: {str(e)}")
        return None


# Extract goals text from pdf
def extract_goals_by_page(pdf_path):
    """
    Extracts pages discussing sustainability or emissions goals.

    Args:
        pdf_path (str): Path to the PDF file.

    Returns:
        str: Extracted text containing goals-related content.
    """
    try:
        reader = PdfReader(pdf_path)
        text = ""
        keywords = ["emission", "carbon", "net-zero", "target", "GHG", "climate", "CO2"]
        YEAR_PATTERN = re.compile(r"\b(?:FY\s?\d{2,4}|\b20[1-3][0-9]\b)", re.IGNORECASE)

        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                lower_text = page_text.lower()
                if any(kw in lower_text for kw in keywords) and YEAR_PATTERN.search(page_text):
                    text += f"\n--- Page ---\n{page_text}\n"

        return text

    except Exception as e:
        print(f"Error processing PDF: {pdf_path}")
        print(f"Error message: {str(e)}")
        return None


def extract_goals_by_paragraph(pdf_path):
    """
    Extracts relevant paragraphs from a PDF that contain sustainability goals.

    Args:
        pdf_path (str): Path to the PDF file.

    Returns:
        str: Extracted text containing goal-related paragraphs.
    """
    try:
        reader = PdfReader(pdf_path)
        text = ""
        keywords = ["emission", "carbon", "net-zero", "target", "GHG", "climate", "CO2"]
        years = ["2023", "2024"]

        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                paragraphs = page_text.split("\n\n")  # 按段落划分
                for para in paragraphs:
                    lower_para = para.lower()
                    if any(kw in lower_para for kw in keywords) and any(yr in lower_para for yr in years):
                        text += f"\n--- Paragraph ---\n{para.strip()}\n"

        return text

    except Exception as e:
        print(f"Error processing PDF: {pdf_path}")
        print(f"Error message: {str(e)}")
        return None


GOALS_ROLE = """
You are a professional sustainability analyst. \
You need to summarize emission reduction targets from corporate ESG reporting. \
"""

GOALS_PROMPT = """
Your answer should be in plain text. Do not use bullet points or markdown formatting. \
According to the given CSR report content, summarize emission reduction targets. \
Include details such as the type of emissions, the reduction percentage (if available), and the target year (if available). \
Ignore unrelated information. Maximum 200 words. \
---------------------------------- \n \
"""


# Find the emission reduction targets using DeepSeek
def call_deepseek_find_goals(company_name, pdf_text):
    """
    Uses DeepSeek LLM to summarize emissions reduction targets from PDF content.

    Args:
        company_name (str): Name of the company.
        pdf_text (str): Relevant text extracted from PDF.

    Returns:
        str: Summary of emissions goals.
    """
    load_dotenv(override=True)
    client = OpenAI(
        api_key= DEEPSEEK_API_KEY,
        base_url="https://api.deepseek.com"
    )

    prompt = f"{GOALS_PROMPT} {pdf_text}"

    # Call the DeepSeek API with timeout
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": GOALS_ROLE},
            {"role": "user", "content": prompt}
        ],
        stream=False
    )

    # Extract the answer text from the response
    answer = response.choices[0].message.content.strip()
    return answer


EMISSIONS_ROLE = """
You are a professional sustainability analyst. \
You need to find the latest scope 1 and scope 2 emissions data of a company from a CSR report. \
"""

EMISSIONS_PROMPT = """
According to the given CSR report content, find the latest scope 1 and scope 2 emissions data. \
Give me the data in the one of following patterns.\n \
##Pattern 1: \n \
Scope 1 (direct): 1,234 unit. \n \
Scope 2 (location-based): 2,345 unit. \n \
Scope 2 (martket-based): 3,456 unit. \n \
##Pattern 2 (only used when scope1 and scope2 are counted together): \n \
Scope 1 and 2 (total): 1,234 unit. \n \
##Requirements: \n \
1. No any explanation needed. \n \
2. Pay attention and try hard to find the unit of the data.\n \
3. Pay more attention in the latter part of the content, as they often contain more accurate and detailed data. \n \
4. Pay attention to the calculation method of Scope 2.\n \
5. If the data is missing or not sure, leave the part as \"N/A\". \n \
---------------------------------- \n
"""

# Convert data from sentence to number, including unit conversion
# Sample input:
#       Scope 1 (direct): 1,234 t CO2e.
#       Scope 2 (location-based): 2,345 t CO2e.
#       Scope 2 (martket-based): 3,456 t CO2e.
# Sample output:
#       (1234, 2345, 3456)
def data_formatting(text):
    """
    Converts textual emission data to a standardized numeric format with proper unit conversion.

    Args:
        text (re.Match): Regex match group containing numeric and unit data.

    Returns:
        str: Converted emission value in metric tonnes as string.
    """
    # Sample input: "49,860.25 tons CO2e."
    try:
        text_value = text.group(1)
        split_text = text_value.replace(",", "").strip().split(" ", 1)  # ['49860.25', 'tons CO2e.']
        value = float(split_text[0])  # 49860.25
        unit = split_text[1].lower().strip()  # tons co2e.
    except:
        return "-"

    ### Default unit is metric ton / t / tonne ###
    # Short ton / ton
    if "short ton" in unit or ("ton" in unit and "metric" not in unit and "tonnes" not in unit):
        value = round(value * 0.90718, 2)
        # Long ton
    elif "long ton" in unit:
        value = round(value * 1.01605, 2)
        # Kilogram / kg
    elif "kilogram" in unit or "kg" in unit:
        value = value / 1000
        if abs(value) < 1:  # If it is a small number, keep three significant digits
            # Find the position of the first non-zero digit
            str_num = f"{value:.10f}"
            first_nonzero = next(i for i, c in enumerate(str_num.replace("-", "").replace("0.", "")) if c != '0')
            value = round(value, first_nonzero + 3)
        else:
            value = round(value, 2)

            # Thousand tonne / kt
    if "thousand" in unit or "kilo tonne" in unit or "kt" in unit:
        value = round(value * 1000, 2)
    # Million tonne / mmt /
    elif "million" in unit or "mmt" in unit:
        value = round(value * 1000000, 2)
    elif "billion" in unit or "gt" in unit:
        value = round(value * 1000000000, 2)

    # If it is an integer, remove the .0 after the decimal point
    if value.is_integer():
        return str(int(value))
    return str(value)


if __name__ == "__main__":
    '''
    # Test single company
    company_name = "APPLE INC"
    emissions_data = find_emissions_data(company_name)
    '''
    # Batch processing
    company = "NVIDIA"
    pdf_path = "filtered_report.pdf"

    goals_text = extract_goals_by_page(pdf_path)
    goals = call_deepseek_find_goals(company, goals_text)
    print("--------------------------------")
    print("Goals:")
    print(goals)
    print("--------------------------------")