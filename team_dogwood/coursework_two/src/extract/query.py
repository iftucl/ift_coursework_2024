#!/usr/bin/env python3
"""
previously: ingest_to_pg.py

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
from src.db_utils.metadata import upsert_metadata_table, create_metadata_table
from src.data_models.metrics import IndicatorList

ESG_PROMPT = r"""
You are an ESG data-extraction function. Return **only** valid JSON, no prose.

Extract for {company}:
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
  "year": year,
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
            # get year, figure
            ry = m.get("year", None)
            fg = m.get("figure", None)
            if any(val is None for val in (ry, fg)):
                continue
            # Coerce year to int
            m["year"] = int(ry)

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
            # TODO: validate company is available in Postgres and read into Company object
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

            # create the schema if it doesn't exist
            db.execute("CREATE SCHEMA IF NOT EXISTS csr_metrics;")
            # Ensure tables exist with correct primary key
            db.execute("""
                CREATE TABLE IF NOT EXISTS csr_metrics.emissions (
                    indicator_id TEXT NOT NULL,
                    indicator_name TEXT,
                    category TEXT,
                    company TEXT,
                    year INTEGER NOT NULL,
                    figure DOUBLE PRECISION,
                    unit TEXT,
                    data_type TEXT,
                    PRIMARY KEY (indicator_id, year)
                );
            """)
            db.execute("""
                CREATE TABLE IF NOT EXISTS csr_metrics.energy (
                    indicator_id TEXT NOT NULL,
                    indicator_name TEXT,
                    category TEXT,
                    company TEXT,
                    year INTEGER NOT NULL,
                    figure DOUBLE PRECISION,
                    unit TEXT,
                    data_type TEXT,
                    PRIMARY KEY (indicator_id, year)
                );
            """)
            db.execute("""
                CREATE TABLE IF NOT EXISTS csr_metrics.waste (
                    indicator_id TEXT NOT NULL,
                    indicator_name TEXT,
                    category TEXT,
                    company TEXT,
                    year INTEGER NOT NULL,
                    figure DOUBLE PRECISION,
                    unit TEXT,
                    data_type TEXT,
                    PRIMARY KEY (indicator_id, year)
                );
            """)
            
            # 4) Loop companies & years
            for company in companies:
                docs = mongo.get_reports_by_company(company)
                if not docs:
                    continue
                
                if args.year and args.company:
                    try:
                        docs = docs.get(args.year)
                    except KeyError:
                        logger.warning(f"No parsed year {args.year} for {company.security}; processing all available years.")
                        docs = docs

                if not docs:
                    logger.warning(f"No parsed years for {company.security}; skipping.")
                    continue
                
                metrics = []
                if isinstance(docs, dict):
                    for year, doc in docs.items():
                        index = VectorStoreIndex.from_documents(doc, embed_model=embed)
                        qe = index.as_query_engine(similarity_top_k=10, llm=llm, output_schema=IndicatorList)

                        logger.info(f"▶ {company.security} / {year}")
                        prompt = ESG_PROMPT.format(company=company.security)
                        rsp = qe.query(prompt)
                        raw = getattr(rsp, "response", None) or rsp.response_text

                        try:
                            # Clean and parse the LLM output
                            metrics = parse_and_strip_json(raw)
                            logger.debug(f"Parsed metrics: {metrics}")
# If metrics is a dict with a 'data' key, extract the list
                            if isinstance(metrics, dict) and "data" in metrics:
                                # metrics = IndicatorList.model_validate(metrics["data"])
                                metrics = metrics["data"]
                            elif isinstance(metrics, list):
                                # metrics = IndicatorList.model_validate(metrics)
                                metrics = metrics
                            else:
                                logger.error(f"Invalid response format for {company.security}/{year}; skipping.")
                                continue
                        except (json.JSONDecodeError, Exception) as e:
                            logger.error(f"Invalid JSON for {company.security}/{year}; skipping. Error: {e}")
                            continue

                        metrics = validate_and_normalize(metrics)
                        emissions = [m for m in metrics if "emissions" in m["category"].lower()]
                        energy = [
                            m for m in metrics
                            if m["indicator_name"].lower().startswith(("total energy", "water"))
                        ]
                        waste = [
                            m for m in metrics
                            if "waste" in m["category"].lower()
                            or "packaging" in m["indicator_name"].lower()
                        ]

                        # Metadata tracking
                        if not (emissions or energy or waste):
                            logger.warning(
                                f"No metrics found for {company.security}/{year}. "
                            )
                        else:
                            if emissions:
                                emissions_metrics_count += len(emissions)
                                emissions_companies.add(company.security)
                                db.upsert_metrics("emissions", emissions)
                            if energy:
                                energy_metrics_count += len(energy)
                                energy_companies.add(company.security)
                                db.upsert_metrics("energy", energy)
                            if waste:
                                waste_metrics_count += len(waste)
                                waste_companies.add(company.security)
                                db.upsert_metrics("waste", waste)
                            logger.success(f"Persisted {company.security}/{year} → Postgres.")

        # Update metadata tables after all companies processed
        create_metadata_table()
        upsert_metadata_table(
            table_name="emissions",
            schema_name="csr_metrics",
            num_metrics=emissions_metrics_count,
            metric_group="emissions",
            num_companies=len(set(emissions_companies)),
        )
        upsert_metadata_table(
            table_name="energy",
            schema_name="csr_metrics",
            num_metrics=energy_metrics_count,
            metric_group="energy",
            num_companies=len(set(energy_companies)),
        )
        upsert_metadata_table(
            table_name="waste",
            schema_name="csr_metrics",
            num_metrics=waste_metrics_count,
            metric_group="waste",
            num_companies=len(set(waste_companies)),
        )
        logger.success("Query pipeline completed successfully.")


if __name__ == "__main__":
    main()

