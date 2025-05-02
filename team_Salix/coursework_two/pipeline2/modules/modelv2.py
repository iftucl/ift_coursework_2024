import csv
import glob
import os
import re
import time

from dotenv import load_dotenv
from openai import APIError, APITimeoutError, OpenAI
from PyPDF2 import PdfReader


def extract_text_from_pdf(pdf_path):
    """
    Extract text from PDF pages containing indicator keywords.

    Args:
        pdf_path (str): Path to the PDF file

    Returns:
        str: Extracted text containing ESG indicators, or None if no relevant text is found

    This function:
    1. Opens and reads the PDF file
    2. Extracts text from each page
    3. Filters pages containing ESG indicator keywords
    4. Combines relevant text from all pages

    Note:
        The function only extracts text from pages containing specific ESG-related keywords
        to improve processing efficiency.
    """
    try:
        reader = PdfReader(pdf_path)
        text = ""
        indicator_keywords = [
            "scope 1",
            "scope 2",
            "energy consumption",
            "water withdrawal",
            "waste generated",
            "employee diversity",
        ]
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                page_text_lower = page_text.lower()
                if any(
                    keyword in page_text_lower 
                    for keyword in indicator_keywords
                ):
                    text += page_text
        return text if text else None
    except Exception as e:
        print(f"Error processing PDF {pdf_path}: {e}")
        return None


def call_api_with_retry(client, messages, model, max_retries=2, timeout=20):
    """
    Helper function to make API calls with retry mechanism.

    Args:
        client (OpenAI): OpenAI client instance
        messages (list): List of message dictionaries for the API call
        model (str): Name of the model to use
        max_retries (int, optional): Maximum number of retry attempts. Defaults to 2.
        timeout (int, optional): Timeout in seconds for API calls. Defaults to 20.

    Returns:
        OpenAI response object

    Raises:
        APITimeoutError: If all retry attempts timeout
        APIError: If all retry attempts fail with API errors
        Exception: For unexpected errors

    This function implements exponential backoff between retry attempts.
    """
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.7,
                timeout=timeout,  # Set timeout in seconds
            )
            return response
        except APITimeoutError:
            if attempt == max_retries - 1:
                print(f"API call timed out after {max_retries} attempts")
                raise
            print(
                f"API call timed out, retrying... "
                f"(Attempt {attempt + 1}/{max_retries})"
            )
            time.sleep(2**attempt)  # Exponential backoff
        except APIError as e:
            if attempt == max_retries - 1:
                print(f"API error after {max_retries} attempts: {e}")
                raise
            print(
                f"API error, retrying... "
                f"(Attempt {attempt + 1}/{max_retries})"
            )
            time.sleep(2**attempt)  # Exponential backoff
        except Exception as e:
            print(f"Unexpected error: {e}")
            raise


def find_data_in_text_grok(company_name, pdf_text):
    """
    Extract ESG indicators using xAI Grok-3-mini API.

    Args:
        company_name (str): Name of the company
        pdf_text (str): Extracted text from the PDF

    Returns:
        str: Formatted ESG indicators data, or None if extraction fails

    This function:
    1. Initializes the OpenAI client with xAI API credentials
    2. Constructs a detailed prompt for ESG data extraction
    3. Makes API calls with retry mechanism
    4. Logs token usage statistics
    5. Returns formatted ESG indicators

    Note:
        The function requires XAI_API_KEY to be set in the environment variables.
    """
    try:
        load_dotenv()
        client = OpenAI(
            api_key=os.getenv("XAI_API_KEY"), 
            base_url="https://api.x.ai/v1"
        )

        prompt = f"""
        Extract the latest data for the following ESG indicators for {company_name} 
        from the provided text. Return the data in the format below, including units 
        where available. If data is missing, use 'N/A'. Focus on the most recent 
        data and prefer detailed sections of the text.

        Format:
        Scope 1 Emissions: <value> tCO2e
        Scope 2 Emissions: <value> tCO2e
        Total Energy Consumption: <value> MWh
        Total Water Withdrawal: <value> m³
        Total Waste Generated: <value> Metric tons
        Employee Diversity: <value> %

        Requirements:
        1. No explanations, only the formatted output.
        2. Ensure correct units as specified.
        3. If units differ, note the original unit in parentheses.
        4. Prioritize data from detailed sections (e.g., tables, summaries).

        Text:
        {pdf_text}
        """

        messages = [
            {
                "role": "system",
                "content": (
                    "You are an expert in extracting ESG data from "
                    "sustainability reports."
                ),
            },
            {"role": "user", "content": prompt},
        ]

        response = call_api_with_retry(client, messages, "grok-3-mini")

        # Log token usage
        usage = response.usage
        print(f"\nToken Usage for {company_name}:")
        print(f"Prompt tokens: {usage.prompt_tokens}")
        print(f"Completion tokens: {usage.completion_tokens}")
        print(f"Total tokens: {usage.total_tokens}")
        if hasattr(usage, "prompt_tokens_details"):
            print(f"Prompt tokens details: {usage.prompt_tokens_details}")

        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Error calling xAI Grok API for {company_name}: {e}")
        return None


def find_data_in_text_deepseek(company_name, pdf_text):
    """
    Extract ESG indicators using DeepSeek API.

    Args:
        company_name (str): Name of the company
        pdf_text (str): Extracted text from the PDF

    Returns:
        str: Formatted ESG indicators data, or None if extraction fails

    This function:
    1. Initializes the OpenAI client with DeepSeek API credentials
    2. Constructs a detailed prompt for ESG data extraction
    3. Makes API calls with retry mechanism
    4. Returns formatted ESG indicators

    Note:
        The function requires DEEPSEEK_API_KEY to be set in the environment variables.
    """
    try:
        load_dotenv()
        client = OpenAI(
            api_key=os.getenv("DEEPSEEK_API_KEY"), 
            base_url="https://api.deepseek.com"
        )

        prompt = f"""
        Extract the latest data for the following ESG indicators for {company_name} 
        from the provided text. Return the data in the format below, including units 
        where available. If data is missing, use 'N/A'. Focus on the most recent 
        data and prefer detailed sections of the text.

        Format:
        Scope 1 Emissions: <value> tCO2e
        Scope 2 Emissions: <value> tCO2e
        Total Energy Consumption: <value> MWh
        Total Water Withdrawal: <value> m³
        Total Waste Generated: <value> Metric tons
        Employee Diversity: <value> %

        Requirements:
        1. No explanations, only the formatted output.
        2. Ensure correct units as specified.
        3. If units differ, note the original unit in parentheses.
        4. Prioritize data from detailed sections (e.g., tables, summaries).

        Text:
        {pdf_text}
        """

        messages = [
            {
                "role": "system",
                "content": (
                    "You are an expert in extracting ESG data from "
                    "sustainability reports."
                ),
            },
            {"role": "user", "content": prompt},
        ]

        response = call_api_with_retry(client, messages, "deepseek-chat")

        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Error calling DeepSeek API for {company_name}: {e}")
        return None


def data_formatting(text, expected_unit):
    """
    Convert extracted data to the expected unit.

    Args:
        text (str): Text containing the value and unit to convert
        expected_unit (str): The target unit for conversion

    Returns:
        str: Formatted value in the expected unit, or "N/A" if conversion fails

    This function:
    1. Extracts numerical value and unit from the input text
    2. Converts the value to the expected unit based on the current unit
    3. Handles various unit conversions for different ESG indicators
    4. Returns formatted value with appropriate precision

    Supported conversions:
        - tCO2e: kg, gigatons, kt, mt
        - MWh: kWh, GWh, TJ
        - m³: liters, km³
        - Metric tons: kg, kt
        - %: decimal ratios
    """
    try:
        if not text or text == "N/A":
            return "N/A"
        match = re.search(r"([\d,\.]+)\s*(.*)", text)
        if not match:
            return "N/A"
        value_str, unit = match.groups()
        value = float(value_str.replace(",", ""))
        unit = unit.lower().strip()

        if expected_unit == "tCO2e":
            if "kg" in unit or "kilogram" in unit:
                value = value / 1000
            elif "gigatons" in unit or "gt" in unit:
                value = value * 1_000_000_000
            elif "kt" in unit or "kiloton" in unit:
                value = value * 1_000
            elif "mt" in unit or "megaton" in unit:
                value = value * 1_000_000
        elif expected_unit == "MWh":
            if "kwh" in unit:
                value = value / 1_000
            elif "gwh" in unit:
                value = value * 1_000
            elif "tj" in unit:
                value = value * 277.778  # 1 TJ = 277.778 MWh
        elif expected_unit == "m³":
            if "liters" in unit or "litres" in unit:
                value = value / 1_000
            elif "km³" in unit:
                value = value * 1_000_000_000
        elif expected_unit == "Metric tons":
            if "kg" in unit or "kilogram" in unit:
                value = value / 1_000
            elif "kt" in unit or "kiloton" in unit:
                value = value * 1_000
        elif expected_unit == "%":
            if "%" not in unit:
                value = value * 100  # Assume ratio if no % unit

        if value.is_integer():
            return str(int(value))
        return str(round(value, 2))
    except Exception as e:
        print(f"Error formatting data: {text}, {e}")
        return "N/A"


def process_esg_data(company_name, year, log_file_path, csv_file_path):
    """
    Process ESG data for a single company and year.

    Args:
        company_name (str): Name of the company
        year (str): Year of the CSR report
        log_file_path (str): Path to the log file
        csv_file_path (str): Path to the output CSV file

    Returns:
        dict: Processed ESG data, or None if processing fails

    This function:
    1. Locates the PDF file for the given company and year
    2. Extracts text from the PDF
    3. Processes the text using both Grok and DeepSeek APIs
    4. Formats and validates the extracted data
    5. Writes results to CSV and log files
    """
    pdf_path = os.path.join("./pipeline1/result/csr_reports", company_name, year, "*.pdf")
    files_path = glob.glob(pdf_path)
    file_path = files_path[0] if files_path else None
    if not file_path:
        print(f"No PDF found for {company_name} in year {year}")
        return None

    pdf_text = extract_text_from_pdf(file_path)
    if not pdf_text:
        print(f"No relevant text extracted for {company_name} in year {year}")
        return None

    with open(log_file_path, "a", encoding="utf-8") as log_file:
        log_file.write(f"\n=========={company_name} - {year}==========\n")

    # Try Grok-3-mini first, fallback to DeepSeek
    data_in_text = find_data_in_text_grok(company_name, pdf_text)
    if not data_in_text:
        data_in_text = find_data_in_text_deepseek(company_name, pdf_text)
    if not data_in_text:
        print(f"No data extracted for {company_name} in year {year}")
        return None

    with open(log_file_path, "a", encoding="utf-8") as log_file:
        log_file.write(f"【Raw Data】\n{data_in_text}\n")

    # Parse and format data
    indicators = [
        ("Scope 1 Emissions", "tCO2e"),
        ("Scope 2 Emissions", "tCO2e"),
        ("Total Energy Consumption", "MWh"),
        ("Total Water Withdrawal", "m³"),
        ("Total Waste Generated", "Metric tons"),
        ("Employee Diversity", "%"),
    ]
    formatted_data = []
    for indicator, unit in indicators:
        match = re.search(rf"{indicator}:\s*([^\n]+)", data_in_text)
        value = data_formatting(match.group(1) if match else "N/A", unit)
        formatted_data.append(value)

    with open(log_file_path, "a", encoding="utf-8") as log_file:
        log_file.write(f"【Formatted Data】\n{', '.join(formatted_data)}\n")

    with open(csv_file_path, "a", encoding="utf-8") as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow([company_name, year] + formatted_data)

    return formatted_data


if __name__ == "__main__":
    # Create logs directory if it doesn't exist
    os.makedirs("./logs", exist_ok=True)

    number = 0
    while os.path.exists(f"./logs/esg_extract_log_{number}.txt"):
        number += 1
    log_file_path = f"./logs/esg_extract_log_{number}.txt"
    csv_file_path = f"./logs/esg_indicators.csv"

    # Write CSV header
    with open(csv_file_path, "w", encoding="utf-8") as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(
            [
                "Company Name",
                "Year",
                "Scope 1 Emissions (tCO2e)",
                "Scope 2 Emissions (tCO2e)",
                "Total Energy Consumption (MWh)",
                "Total Water Withdrawal (m³)",
                "Total Waste Generated (Metric tons)",
                "Employee Diversity (%)",
            ]
        )

    reports_dir = "./pipeline1/result/csr_reports"
    # Process each company folder
    for company_name in os.listdir(reports_dir):
        company_path = os.path.join(reports_dir, company_name)
        if os.path.isdir(company_path):
            # Process each year folder
            for year in os.listdir(company_path):
                year_path = os.path.join(company_path, year)
                if os.path.isdir(year_path):
                    process_esg_data(company_name, year, log_file_path, csv_file_path)
