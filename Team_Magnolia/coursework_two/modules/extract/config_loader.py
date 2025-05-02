# coursework_two/modules/config_loader.py
# -*- coding: utf-8 -*-
"""
Central configuration loader
───────────────────────────────────────────────────────────────────────────────
* Reads YAML config (`config/conf.yaml`)
* Resolves paths (BASE_DIR / output / resources …)
* Exposes constants for the rest of the code-base
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Dict, Any

import yaml  # PyYAML is already declared in pyproject.toml

# ──────────────────────────────────────────────────────────────────────────────
# 0)  Paths & helpers
# ──────────────────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent.parent           # repo_root/coursework_two
CONF_PATH = BASE_DIR / "config" / "conf.yaml"
RESOURCE_D = BASE_DIR / "resources"                         # auxiliary files
OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_DIR.mkdir(exist_ok=True, parents=True)


def _read_yaml(path: Path) -> Dict[str, Any]:
    """Return YAML file content as dict (raises on syntax error / missing)."""
    if not path.exists():
        raise FileNotFoundError(f"YAML file not found: {path}")
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


# ──────────────────────────────────────────────────────────────────────────────
# 1)  Main conf.yaml
# ──────────────────────────────────────────────────────────────────────────────
_cfg = _read_yaml(CONF_PATH)

# ──────────────────────────────────────────────────────────────────────────────
# 2)  PDF source
# ──────────────────────────────────────────────────────────────────────────────
PDF_PATH = Path(_cfg.get("pdf_path", ""))        # local path
PDF_OBJECT_KEY = _cfg.get("pdf_object_key")      # MinIO key

# ──────────────────────────────────────────────────────────────────────────────
# 3)  Output filenames
# ──────────────────────────────────────────────────────────────────────────────
OUTPUT_PDF = _cfg.get("output_pdf", "filtered_report_pages.pdf")
OUTPUT_MD = _cfg.get("output_md", "filtered_report_parsed.md")
OUTPUT_JSON = _cfg.get("output_json", "extracted_data.json")
FINAL_JSON = _cfg.get("final_json", "final_standardized.json")
OUTPUT_CSV = _cfg.get("output_csv", "standardized_data.csv")

# ──────────────────────────────────────────────────────────────────────────────
# 4)  Groq LLM  ➜  **Hard-coded fallback API key added here**
# ──────────────────────────────────────────────────────────────────────────────
_DEFAULT_GROQ_API_KEY = "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"

GROQ_API_KEY = os.getenv(
    "GROQ_API_KEY",
    _cfg.get("groq_api_key") or _DEFAULT_GROQ_API_KEY
)
GROQ_BASE_URL = _cfg.get("groq_base_url", "https://api.groq.com/openai/v1")
GROQ_MODEL = _cfg.get("groq_model", "meta-llama/llama-4-scout-17b-16e-instruct")

# ──────────────────────────────────────────────────────────────────────────────
# 5)  Docling page-break
# ──────────────────────────────────────────────────────────────────────────────
PAGE_BREAK = _cfg.get("page_break", "---TEMP_DOCLING_PAGE_BREAK---")

# ──────────────────────────────────────────────────────────────────────────────
# 6)  MinIO
# ──────────────────────────────────────────────────────────────────────────────
_minio = _cfg.get("minio", {})
MINIO_ENDPOINT = _minio.get("endpoint")
MINIO_ACCESS_KEY = _minio.get("access_key")
MINIO_SECRET_KEY = _minio.get("secret_key")
MINIO_BUCKET = _minio.get("bucket")
MINIO_SECURE = bool(_minio.get("secure", False))

# ──────────────────────────────────────────────────────────────────────────────
# 7)  Database
# ──────────────────────────────────────────────────────────────────────────────
database = _cfg.get("database", {})
MONGO_URI = database.get("mongo_uri")
MONGO_DB = database.get("mongo_db")
POSTGRES_URI = database.get("postgres_uri")
POSTGRES_SCHEMA = database.get("postgres_schema")

# ──────────────────────────────────────────────────────────────────────────────
# 8)  Data catalogue & dictionary
# ──────────────────────────────────────────────────────────────────────────────
DATA_CATALOGUE = BASE_DIR / _cfg.get("data_catalogue", "modules/db/data_catalogue.csv")

_dict_file = BASE_DIR / _cfg.get("data_dictionary", "data_dictionary.yaml")
DATA_DICT = _read_yaml(_dict_file)

if not isinstance(DATA_DICT, dict):
    raise TypeError(
        "DATA_DICT must be <dict>, got "
        f"{type(DATA_DICT)}. Check {_dict_file} – it should be a YAML mapping."
    )

# ──────────────────────────────────────────────────────────────────────────────
# 9)  Year regex & theme definitions
# ──────────────────────────────────────────────────────────────────────────────
YEAR_PATTERN = _cfg.get(
    "year_pattern",
    r"\b(?:FY|FISCAL\s*YEAR)?\s*(?:20\d{2}|['‘’]?\d{2})\b",
)
YEAR_RE = re.compile(YEAR_PATTERN, re.I)


def _theme(unit: str, keywords: list[str], **kw) -> dict:
    """Build theme dict with compiled regex patterns."""
    goal_kw = kw.pop(
        "goal_keywords",
        [r"\b(2030|2050)\b", r"\b(target|goal)s?\b", r"\b(baseline(?:\s*year)?|base\s*year)\b"],
    )
    cfg: dict[str, Any] = dict(unit=unit, keywords=keywords, goal_keywords=goal_kw, **kw)

    cfg["unit_re"] = re.compile(cfg["unit"], re.I)
    cfg["keyword_re"] = [re.compile(k, re.I) for k in cfg["keywords"]]
    cfg["goal_kw_re"] = [re.compile(k, re.I) for k in cfg["goal_keywords"]]
    if cfg.get("extras"):
        cfg["extra_re"] = [re.compile(e, re.I) for e in cfg["extras"]]
    return cfg


THEMES: dict[str, dict] = {
    name: _theme(
        unit=section["unit"],
        keywords=section.get("keywords", []),
        require_multiple_year_occurrences=section.get("require_multiple_year_occurrences", False),
        min_keyword_hits=section.get("min_keyword_hits", 1),
        extras=section.get("extras", []),
    )
    for name, section in _cfg.get("themes", {}).items()
}
