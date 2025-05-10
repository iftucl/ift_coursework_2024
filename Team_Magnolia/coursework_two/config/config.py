"""
Sustainability Report Data Extraction Configuration

This module centralizes configuration settings and constants used by the
sustainability data extractor.
"""

import os
import re
from pathlib import Path

# ─── 基础路径 ────────────────────────────────────────────────────────────────
BASE_DIR   = Path(__file__).parent.parent       # 项目根目录
OUTPUT_DIR = BASE_DIR / "coursework_two" / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ─── PDF 来源键（MinIO object key）────────────────────────────────────────────
# 必须通过环境变量传入，例如:
# export PDF_OBJECT_KEY="reports/2024_NVIDIA_CSR_Report.pdf"
PDF_OBJECT_KEY = os.getenv("PDF_OBJECT_KEY")
if not PDF_OBJECT_KEY:
    raise RuntimeError("Environment variable PDF_OBJECT_KEY is required for MinIO PDF retrieval")

# ─── 输出文件名 ───────────────────────────────────────────────────────────────
OUTPUT_PDF  = os.getenv("OUTPUT_PDF",  "filtered_report_pages.pdf")
OUTPUT_MD   = os.getenv("OUTPUT_MD",   "filtered_report_parsed.md")
OUTPUT_JSON = os.getenv("OUTPUT_JSON", "extracted_data.json")

# ─── LLM 抽取配置 ────────────────────────────────────────────────────────────
GROQ_API_KEY  = os.getenv("GROQ_API_KEY")
GROQ_BASE_URL = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")
GROQ_MODEL    = os.getenv("GROQ_MODEL",    "meta-llama/llama-4-scout-17b-16e-instruct")

# Page break marker for Docling
PAGE_BREAK = "---TEMP_DOCLING_PAGE_BREAK_SPECIAL---"

# Common regex patterns
YEAR = r"\b(?:FY|FISCAL\s*YEAR)?\s*(?:20\d{2}(?:\/\d{2})?|['\u2018\u2019']?\d{2})\b"
YEAR_RE = re.compile(YEAR, re.I)

# Common goal keywords for all themes
_GOALS = [
    r"\b(2030|2050)\b", 
    r"\b(target|goal)s?\b", 
    r"\b(baseline(?:\s*year)?|base\s*year)\b"
]

# Helper function for theme definition
def theme(unit, keywords, **kwargs):
    """Create a theme configuration with common defaults."""
    return dict(
        unit=unit,
        keywords=keywords,
        goal_keywords=_GOALS,
        **kwargs,
    )

# Theme definitions with their regex patterns
THEMES = {
    "GHG Emissions": theme(
        unit=r"\b(?:\d[\d,.]*\s*)?(?:tco2e|t\s*co2e|tco2-e|mtco2e|mt\s*co2e|ktco2e|kt\s*co2e|co2e|co₂e|co2-eq|co₂-eq|mtco₂e|ktco₂e|metric\s*tons?\s*(?:of\s*)?co2e|metric\s*tons?\s*(?:of\s*)?co₂e|metric\s*tonnes?\s*(?:of\s*)?co2e|metric\s*tonnes?\s*(?:of\s*)?co₂e|mt|kt|tons?|tonnes?)\b",
        keywords=[
            r"\b(scope\s*1|scope\s*one)\b",
            r"\b(scope\s*2|scope\s*two)\b",
            r"\b(scope\s*3|scope\s*three)\b",
            r"\b(ghg|greenhouse\s*gas(?:es)?|emissions)\b",
        ],
        require_multiple_year_occurrences=True,
        min_keyword_hits=2,
    ),
    "Energy": theme(
        unit=r"\b(?:MWh|GWh|kWh|GJ|MJ|TJ|PJ|kBtu|MMBtu|(?:MWh|GWh|kWh)\s*\/\s*\$?M(?:\s*Revenue)?|\d[\d,.]*\s*%)\b",
        keywords=[
            r"\benergy\s+consumption\b",
            r"\belectricity\s+usage\b",
            r"\belectricity\s+consumption\b",
            r"\brenewable\s+electricity(?:\s+consumption)?\b",
            r"\brenewable\s+energy\b",
            r"\belectricity\s+production\b",
            r"\bpower\s+use\b",
            r"\belectricity\s+use\b",
            r"\b(?:generated|purchased)\s+electricity\b"
        ],
        require_multiple_year_occurrences=True,
        min_keyword_hits=2,
    ),
    "Water": theme(
        unit=r"\b(?:ML|Megalitres?|Megaliters?|m³|m3|cubic\s+meters?|cubic\s+metres?|gallons?|lit(?:er|re)s?|acre[- ]?f(?:ee|oo)?t|kL|GL|mcf|thousand\s+cubic\s+feet|\d[\d,.]*\s*%)\b",
        keywords=[
            r"\b(water\s+(?:discharge|withdrawal|consumption)|(?:discharge|withdrawal|consumption)\s+of\s+water)\b",
            r"\b(freshwater|water\s+(?:use|usage|efficiency))\b",
        ],
        require_multiple_year_occurrences=True,
    ),
    "Operational Waste": theme(
        unit=r"\b(?:(?:metric\s+)?(?:tons?|tonnes?)|kt|kmt|kg|kilograms?|m³|m3|cubic\s+meters?|cubic\s+metres?|\d[\d,.]*\s*%)\b",
        keywords=[
            r"\bwaste\b",
        ],
        extras=[
            r"\b(hazardous|non[- ]?hazardous|diversion\s+rate)\b",
            r"\bdiverted\b",
            r"\blandfill\b",
            r"\bsent\b",
        ],
    ),
    "Product Circularity": theme(
        unit=r"\b(?:\d[\d,.]*\s*(?:%|percent|#|tonnes?|tons?|metric\s+tons?))\b",
        keywords=[
            r"\brecycled\s+material\s+content\b",
            r"\bpackaging\s+recyclability\b",
            r"\bplastic\s+in\s+packaging\b",
            r"\bsingle[- ]?use\s+plastic(?:s)?\b",
            r"\b(?:recycled|sustainable)\s+fib(?:er|re)\s+in\s+packaging\b",
            r"\b(?:plastic|products?)\s+take[\s-]?back\b",
            r"\bproducts?\s+refurbished\b",
            r"\bpackaging\b\b",
        ],
        min_keyword_hits=1,
        require_multiple_year_occurrences=True,
    ),
    "Social": theme(
        unit=r"\b(?:\d[\d,.]*\s*)?(?:%|percent|\$|#|hours?|hrs?|rate(?:s)?\s*/\s*200k\s*hrs?)\b",
        keywords=[
            r"\b(headcount|employees?|workforce|gender|women|men|ethnicity|race|diversity|representation)\b",
            r"\b(training\s+hours?|volunteering\s+hours?|donations?|community\s+investment)\b",
            r"\b(recordable\s+injury\s+rate|rir|trir|lost\s*time\s+injury\s+rate|ltir|fatalities?)\b",
        ],
        min_keyword_hits=2,
    ),
    "Governance": theme(
        unit=r"\b(?:\d[\d,.]*\s*)?(?:%|percent|#)\b",
        keywords=[
            r"\b(board\s+members?|directors?)\b",
            r"\b(independent\s+directors?|board\s+independence)\b",
            r"\b(board\s+diversity|women\s+directors?|underrepresented\s+groups?|ethnic\s+minorities)\b",
        ],
    ),
}

# Pre-compile regex patterns
for cfg in THEMES.values():
    cfg["unit_re"] = re.compile(cfg["unit"], re.I)
    cfg["keyword_re"] = [re.compile(k, re.I) for k in cfg["keywords"]]
    cfg["goal_kw_re"] = [re.compile(k, re.I) for k in cfg["goal_keywords"]]
    if "extras" in cfg:
        cfg["extra_re"] = [re.compile(e, re.I) for e in cfg["extras"]] 