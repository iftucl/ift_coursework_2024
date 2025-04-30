#!/usr/bin/env python3
"""
Load parsed CSR pages from MongoDB, build an in‐memory vector index,
prompt GPT-4 to extract nine ESG metrics as JSON, validate/normalize
them, and UPSERT into three PostgreSQL tables:

  * emissions – Scope 1/2/3
  * energy    – energy + water
  * waste     – waste + packaging

By default, processes ALL companies & years in Mongo.  Use --company
and/or --year to restrict.
"""

import argparse
import json
import os
import re
import sys
from typing import List, Dict

from loguru import logger
from llama_index.core import VectorStoreIndex
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.llms.openai import OpenAI

sys.path.append(os.path.join(os.path.dirname(__file__), "../.."))

from src.db_utils.mongo import MongCollection
from src.db_utils.postgres import PostgreSQLDB
from config.models import model_settings
from src.db_utils.metadata import upsert_metadata_table

ESG_PROMPT = r"""
You are an ESG data-extraction function. Return **only** valid JSON, no prose.

Extract for {company} {year}:
  1. Scope 1 GHG emissions
  2. Scope 2 GHG emissions
  3. Scope 3 GHG emissions
  4. Total energy consumption / usage
  5. Water consumption
  6. Water recycled / reused
  7. Total waste generated
  8. Product packaging recyclability
  9. Packaging waste

Each element example:
{{
  "indicator_id": "IND_001",
  "indicator_name": "Scope 1 GHG Emissions",
  "category": "Climate / Emissions",
  "company": "{company}",
  "report_year": {year},
  "figure": 68.82,
  "unit": "million tCO₂e",
  "data_type": "float"
}}
"""

def parse_and_strip_json(raw: str) -> List[Dict]:
    """
    Strip any Markdown/JSON code fences and parsed GPT-4 output.

    :param raw: Raw response text from the LLM.
    :type raw: str
    :return: List of metric dicts.
    :rtype: list[dict]
    :raises json.JSONDecodeError: If the cleaned text is not valid JSON.
    """
    clean = re.sub(r"^```json\s*|\s*```$", "", raw.strip(),
                   flags=re.IGNORECASE | re.DOTALL)
    return json.loads(clean)


def validate_and_normalize(metrics: List[Dict]) -> List[Dict]:
    """
    Validate and normalize a list of ESG metric dicts.

    - Coerce 'figure' to float or int based on 'data_type'.
    - Normalize 'unit' to a lowercase, trimmed string.
    - Drop metrics where 'figure' cannot be parsed.

    :param metrics: Raw metric dicts from GPT-4.
    :type metrics: list[dict]
    :return: Cleaned list of metric dicts.
    :rtype: list[dict]
    """
    out = []
    for m in metrics:
        try:
            # figure → float/int
            raw = m.get("figure")
            val = float(str(raw).replace(",", ""))
            if m.get("data_type", "").lower() == "integer":
                m["figure"] = int(round(val))
            else:
                m["figure"] = val

            # unit → lowercase trimmed
            unit = str(m.get("unit", "")).strip().lower()
            m["unit"] = unit or "unknown"

            out.append(m)
        except Exception as e:
            logger.warning(f"Dropping metric {m.get('indicator_id')} – {e}")
    return out


def main() -> None:
    """
    Entry point: parse CLI args, read from Mongo, prompt GPT-4, validate
    metrics, and upsert into Postgres.

    Flags:
      --company:   Single company.security to process.
      --year:      Single year to process (requires --company).
    """
    parser = argparse.ArgumentParser(
        description="Ingest ESG KPIs from Mongo -> GPT-4 -> PostgreSQL."
    )
    parser.add_argument(
        "--company",
        default=None,
        help="Ticker/security to process (e.g. AAPL). Omit to process all.",
    )
    parser.add_argument(
        "--year",
        default=None,
        type=int,
        help="Report year to process (requires --company). Omit to process all years.",
    )
    args = parser.parse_args()

    # 1) Mongo & company list
    with MongCollection() as mongo:
        if args.company:
            companies = [args.company]
        else:
            companies = mongo.get_available_companies()
        logger.info(f"Processing {len(companies)} companies…")

        # 2) LLM & embedding
        embed = HuggingFaceEmbedding(model_name=model_settings.EMBEDDINGS_MODEL_NAME)
        llm = OpenAI(model=model_settings.OPENAI_MODEL_NAME, api_key=model_settings.OPENAI_API_KEY)

        # 3) Postgres
        with PostgreSQLDB() as db:
            # Metadata tracking
            emissions_metrics_count = 0
            energy_metrics_count = 0
            waste_metrics_count = 0
            emissions_companies = set()
            energy_companies = set()
            waste_companies = set()
            # 4) Loop companies & years
            for company in companies:
                doc = mongo.get_report_by_company(company)
                if not doc:
                    continue

                years = [args.year] if (args.year and args.company) else mongo.get_available_years(doc)

                if not years:
                    logger.warning(f"No parsed years for {company}; skipping.")
                    continue
                
                index = VectorStoreIndex.from_documents(doc, embed_model=embed)
                qe = index.as_query_engine(similarity_top_k=10, llm=llm)

                for yr in years:
                    logger.info(f"▶ {company} / {yr}")
                    prompt = ESG_PROMPT.format(company=company, year=yr)
                    rsp = qe.query(prompt)
                    raw = getattr(rsp, "response", None) or rsp.response_text

                    try:
                        metrics = parse_and_strip_json(raw)
                    except json.JSONDecodeError:
                        logger.error(f"Invalid JSON for {company}/{yr}; skipping.")
                        continue

                    metrics = validate_and_normalize(metrics)
                    emissions = [m for m in metrics if "emissions" in m["category"].lower()]
                    energy    = [
                        m for m in metrics
                        if m["indicator_name"].lower().startswith(("total energy", "water"))
                    ]
                    waste     = [
                        m for m in metrics
                        if "waste" in m["category"].lower()
                        or "packaging" in m["indicator_name"].lower()
                    ]

                    # Metadata tracking
                    if emissions:
                        emissions_metrics_count += len(emissions)
                        emissions_companies.add(company)
                    if energy:
                        energy_metrics_count += len(energy)
                        energy_companies.add(company)
                    if waste:
                        waste_metrics_count += len(waste)
                        waste_companies.add(company)

                    db.upsert_metrics("emissions", emissions)
                    db.upsert_metrics("energy", energy)
                    db.upsert_metrics("waste", waste)
                    logger.success(f"Persisted {company}/{yr} → Postgres.")

        # Update metadata tables after all companies processed
        upsert_metadata_table(
            table_name="emissions",
            schema_name="csr_metrics",
            num_metrics=emissions_metrics_count,
            metric_group="emissions",
            num_companies=len(emissions_companies),
        )
        upsert_metadata_table(
            table_name="energy",
            schema_name="csr_metrics",
            num_metrics=energy_metrics_count,
            metric_group="energy",
            num_companies=len(energy_companies),
        )
        upsert_metadata_table(
            table_name="waste",
            schema_name="csr_metrics",
            num_metrics=waste_metrics_count,
            metric_group="waste",
            num_companies=len(waste_companies),
        )
        logger.success("Query pipeline completed successfully.")


if __name__ == "__main__":
    main()
