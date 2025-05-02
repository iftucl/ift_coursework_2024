"""
Handles extraction of CSR indicators from PDF files using DeepSeek API.

Includes text parsing, relevance detection, DeepSeek querying, postprocessing, and CSV output.
"""

import csv
import difflib
import logging
import os
import re
from datetime import datetime
from io import BytesIO
from pathlib import Path

import requests
from dotenv import load_dotenv
from pypdf import PdfReader

from modules.input.indicator_config import load_indicator_config
from modules.input.postprocess import postprocess_value

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


UNIT_PATTERN = re.compile(
    r"\b\d{1,3}(?:,\d{3})*(?:\.\d+)?\s*"
    r"(?:"
    r"%|percent|"
    r"tonnes?|tons?|mtco2e?|"
    r"co2[ e]?|co₂[ e]?|ghg|"
    r"cubic\s?meters?|m³|"
    r"mwh|kwh|gwh|"
    r"kg|kilo(?:grams?)?|"
    r"lit(?:ers?|res?)|gallons?|"
    r"btu|joules?|"
    r"ppm|ppb|"
    r"kw|mw|gw"
    r")\b",
    flags=re.IGNORECASE,
)


def build_alias_map(indicator_config):
    """
    Builds a mapping from indicator aliases to canonical indicator names.

    Args:
        indicator_config (list): List of indicator group configurations.

    Returns:
        dict: Mapping from alias (lowercase) to canonical indicator name.
    """
    alias_map = {}
    for group in indicator_config:
        for ind in group["indicators"]:
            canonical = ind["name"].strip()
            alias_map[canonical.lower()] = canonical
            for alias in ind.get("aliases", []):
                alias_map[alias.strip().lower()] = canonical
    return alias_map


def build_indicator_labels(indicator_config):
    """
    Builds a flat list of all indicator names and aliases.

    Args:
        indicator_config (list): List of indicator group configurations.

    Returns:
        list: List of indicator names and aliases.
    """

    labels = []
    for group in indicator_config:
        for ind in group["indicators"]:
            labels.append(ind["name"])
            for alias in ind.get("aliases", []):
                labels.append(alias)
    return labels


def extract_keywords(indicator_config: list) -> set:
    """
    Extracts all indicator names and aliases into a set of lowercase keywords.

    Args:
        indicator_config (list): List of indicator group configurations.

    Returns:
        set: Set of keywords for indicator matching.
    """
    keywords = set()
    for group in indicator_config:
        for ind in group["indicators"]:
            keywords.add(ind["name"].lower())
            for alias in ind.get("aliases", []):
                keywords.add(alias.lower())
    return keywords


def is_relevant_chunk(text: str, keywords: set) -> bool:
    """
    Determines if a text chunk is relevant based on presence of keywords and units.

    Args:
        text (str): Text chunk to evaluate.
        keywords (set): Set of indicator keywords.

    Returns:
        bool: True if the chunk is relevant, False otherwise.
    """
    text_lower = text.lower()
    has_keyword = any(
        re.search(rf"\b{re.escape(keyword)}\b", text_lower) for keyword in keywords
    )
    has_unit = bool(UNIT_PATTERN.search(text_lower))
    return has_keyword and has_unit


session = requests.Session()


def query_deepseek(
    api_key: str, pdf_text: str, indicator_config: list, extract_header: bool = False
) -> str:
    """
    Sends extracted PDF text to DeepSeek API for CSR indicator extraction.

    Args:
        api_key (str): DeepSeek API key.
        pdf_text (str): Text extracted from the PDF.
        indicator_config (list): Indicator configuration for prompts.
        extract_header (bool, optional): Whether to only extract header metadata. Defaults to False.

    Returns:
        str: DeepSeek API extracted text response.
    """
    all_labels = build_indicator_labels(indicator_config)
    indicator_prompt_list = "\n".join([f"- {label}" for label in all_labels])

    if extract_header:
        prompt = f"""
Extract the **report year** from the first page of this CSR report.

Respond in this format:
Report Year: [year]

--- BEGIN TEXT ---
{pdf_text}
--- END TEXT ---
"""
    else:
        prompt = f"""
Extract the **company name** and the **latest available numeric value** for **each indicator**, using the main name or any listed alias (even if not a perfect match).

Respond in this format:

Company Name: [company name]
- Indicator Name: [numeric value] [unit]

{indicator_prompt_list}

** Guidelines for extraction:**
   - Use exact or close semantic matches (e.g., "Waste Recycled" ≈ "Recycling Rate").
   - Prioritize **absolute values** for absolute metrics ((Carbon Emissions, Water Use, Renewable Energy) and percentages for ratio based metrics (Recycling Rate, Sustainable Materials)  .
   - If only percentages are found, return them (e.g., "23%").
   - If multiple aliases appear, pick the **most precise** number.
   - Do NOT return unrelated stats (e.g., GDP, revenue, employee count, monetary values).
   - Accept estimates if unit is missing but context suggests correctness.
   - If **no valid data exists**, return "N/A".
   - Never return qualitative terms like “pledged”, “projects”, or “initiatives”.

--- BEGIN TEXT ---
{pdf_text}
--- END TEXT ---
"""

    url = "https://api.deepseek.com/v1/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": "You are a sustainability data analyst."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.2,
    }

    response = session.post(url, json=payload, headers=headers)
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"].strip()


def extract_indicators_from_bytes(
    company_name: str,
    pdf_bytes: BytesIO,
    config_path: Path,
    output_csv: Path,
    log_path: Path,
    source_filename: str = "unknown_file.pdf",
):
    """
    Extracts CSR indicators from a PDF byte stream and saves results to CSV.

    Args:
        company_name (str): Company name for labeling extracted data.
        pdf_bytes (BytesIO): Byte stream of the PDF file.
        config_path (Path): Path to the indicators configuration YAML.
        output_csv (Path): Path to save extracted CSV output.
        log_path (Path): Path to save extraction logs.
        source_filename (str, optional): Source file name for lineage tracking. Defaults to "unknown_file.pdf".

    Returns:
        tuple[dict, list]:
            - Dictionary mapping indicator names to extracted values.
            - List of extracted lineage records for audit purposes.
    """
    load_dotenv()
    api_key = os.getenv("DEEPSEEK_API")
    if not api_key:
        raise EnvironmentError("DEEPSEEK_API not found in environment.")

    reader = PdfReader(pdf_bytes, strict=False)
    indicator_config = load_indicator_config(config_path)
    alias_map = build_alias_map(indicator_config)
    keywords = extract_keywords(indicator_config)

    first_page_text = reader.pages[0].extract_text() or ""
    header_result = query_deepseek(
        api_key, first_page_text, indicator_config, extract_header=True
    )

    extracted_company_name = company_name
    extracted_year = "N/A"
    for line in header_result.splitlines():
        line = line.strip()
        if line.lower().startswith("company name:"):
            extracted_company_name = line.split(":", 1)[1].strip()
        elif line.lower().startswith("report year:"):
            value = line.split(":", 1)[1].strip()
            if re.fullmatch(r"\d{4}", value):
                extracted_year = value

    relevant_text = []
    for i, page in enumerate(reader.pages):
        try:
            text = page.extract_text() or ""
            if is_relevant_chunk(text, keywords):
                relevant_text.append(text)
        except Exception as e:
            logger.warning(f"Failed to extract text from a page: {e}")
            continue
    if not relevant_text:
        logger.warning(f"No relevant text found in {source_filename}.")
        return {}, []

    big_text = "\n".join(relevant_text)
    try:
        result_text = query_deepseek(api_key, big_text, indicator_config)
    except Exception as e:
        logger.warning(f"Deepseek query failed: {e}")
        return {}, []

    temp_lineage_map = {}
    final_response = {}
    lineage_records = []

    for line in result_text.splitlines():
        line = line.strip()
        try:
            if line.lower().startswith("company name:"):
                extracted_company_name = line.split(":", 1)[1].strip()
                continue
            elif line.lower().startswith("report year:"):
                continue
            match = re.match(r"^-?\s*(.*?):\s*(.*)", line)
            if match:
                name, value = match.groups()
                normalized_name = name.strip().lower()
                canonical_name = alias_map.get(normalized_name)

                if not canonical_name:
                    fuzzy_match = difflib.get_close_matches(
                        normalized_name, alias_map.keys(), n=1, cutoff=0.8
                    )
                    if fuzzy_match:
                        canonical_name = alias_map[fuzzy_match[0]]

                if canonical_name:
                    matched_ind = next(
                        (
                            ind
                            for group in indicator_config
                            for ind in group["indicators"]
                            if ind["name"] == canonical_name
                        ),
                        None,
                    )
                    if matched_ind:
                        expected_unit = matched_ind.get("unit")
                        rules = matched_ind.get("validation", {})
                        expected_type = matched_ind.get("expected_type", "float")
                        aim = matched_ind.get("aim", "reduction")
                    else:
                        expected_unit, rules = None
                        rules = {}
                        expected_type = "float"
                        aim = "reduction"

                    postprocessed = postprocess_value(
                        value,
                        expected_unit,
                        rules,
                        expected_type=expected_type,
                        aim=aim,
                    )

                    if (
                        canonical_name not in final_response
                        or final_response[canonical_name] == "N/A"
                    ):
                        final_response[canonical_name] = postprocessed["normalized"]
                        temp_lineage_map[canonical_name] = {
                            "value": postprocessed["normalized"],
                            "source_file": source_filename,
                            "extracted_at": datetime.now().isoformat(),
                        }

                    if postprocessed["normalized"].strip().upper() != "N/A":
                        if not postprocessed["valid"]:
                            logger.warning(f"[{canonical_name}] '{value}' → Invalid")
                        elif postprocessed["warning"]:
                            logger.info(
                                f"[{canonical_name}] '{value}' → Exceeds threshold"
                            )

        except Exception as e:
            logger.warning(f"Line failed: '{line}' → {e}")

    log_path.parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, "a", encoding="utf-8") as log_file:
        log_file.write(
            f"\n======== {extracted_company_name} ({extracted_year}) ========\n"
        )
        for k, v in final_response.items():
            log_file.write(f"{k}: {v}\n")

    header = ["Company Name", "Report Year"]
    output_data = [extracted_company_name, extracted_year]

    for group in indicator_config:
        for ind in group["indicators"]:
            indicator_name = ind["name"]
            header.append(indicator_name)
            matched_value = final_response.get(indicator_name, "N/A")
            output_data.append(matched_value)

    output_csv.parent.mkdir(parents=True, exist_ok=True)
    write_header = not output_csv.exists()

    with open(output_csv, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if write_header:
            writer.writerow(header)
        writer.writerow(output_data)

    lineage_output_csv = output_csv.parent / "lineage_output.csv"
    write_lineage_header = not lineage_output_csv.exists()

    with open(lineage_output_csv, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "company_name",
                "report_year",
                "indicator",
                "value",
                "source_file",
                "extracted_at",
            ],
        )
        if write_lineage_header:
            writer.writeheader()
        for canonical_name, record in temp_lineage_map.items():
            row = {
                "company_name": extracted_company_name,
                "report_year": extracted_year,
                "indicator": canonical_name,
                "value": record["value"],
                "source_file": record["source_file"],
                "extracted_at": record["extracted_at"],
            }
            writer.writerow(row)
            lineage_records.append(row)

    logger.info(f"Lineage CSV saved for {extracted_company_name} ({extracted_year})")
    return final_response, lineage_records
