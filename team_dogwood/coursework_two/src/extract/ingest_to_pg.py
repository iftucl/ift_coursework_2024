# src/extract/ingest_to_pg.py

#!/usr/bin/env python3
"""
ingest_to_pg.py
===============

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
from typing import List, Dict, Optional

import psycopg2
from dotenv import load_dotenv
from loguru import logger
from llama_index.core import Document, VectorStoreIndex
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.llms.openai import OpenAI

from src.db_utils.mongo import MongCollection

# load .env for OPENAI_*, DB_POSTGRES_*, MONGO_*, MODEL_NAME, etc.
load_dotenv()


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
    Strip any Markdown/JSON code fences and parse GPT-4 output.

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


def upsert_many(cur, table: str, rows: List[Dict]) -> None:
    """
    Bulk UPSERT a list of metrics into the specified Postgres table.

    :param cur: Psycopg2 cursor (open transaction).
    :param table: Table name ('emissions', 'energy', or 'waste').
    :param rows: List of metric dicts containing matching columns.
    """
    if not rows:
        return
    cols = list(rows[0].keys())
    cols_csv = ", ".join(cols)
    placeholders = ", ".join(["%s"] * len(cols))
    updates = ", ".join(f"{c}=EXCLUDED.{c}" for c in cols if c != "indicator_id")
    sql = (
        f"INSERT INTO {table} ({cols_csv}) VALUES ({placeholders}) "
        f"ON CONFLICT (indicator_id) DO UPDATE SET {updates};"
    )
    cur.executemany(sql, [tuple(r[c] for c in cols) for r in rows])


def main() -> None:
    """
    Entry point: parse CLI args, read from Mongo, prompt GPT-4, validate
    metrics, and upsert into Postgres.

    Flags:
      --company:   Single company.security to process.
      --year:      Single year to process (requires --company).
      --openai_model: Override default LLM model.
      --openai_key:   Override default API key.
    """
    parser = argparse.ArgumentParser(
        description="Ingest ESG KPIs from Mongo ↦ GPT-4 ↦ PostgreSQL."
    )
    parser.add_argument(
        "--company",
        help="Ticker/security to process (e.g. AAPL). Omit to process all.",
    )
    parser.add_argument(
        "--year",
        type=int,
        help="Report year to process (requires --company). Omit to process all years.",
    )
    parser.add_argument(
        "--openai_model",
        default=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        help="OpenAI model to use.",
    )
    parser.add_argument(
        "--openai_key",
        default=os.getenv("OPENAI_API_KEY"),
        help="OpenAI API key.",
    )
    args = parser.parse_args()

    # 1) Mongo & company list
    with MongCollection() as mongo:
        if args.company:
            companies = [args.company]
        else:
            companies = mongo.list_companies()
        logger.info(f"Processing {len(companies)} companies…")

        # 2) LLM & embedding
        embed_model = os.getenv("MODEL_NAME", "all-MiniLM-L6-v2")
        embed = HuggingFaceEmbedding(model_name=embed_model)
        llm = OpenAI(model=args.openai_model, api_key=args.openai_key)

        # 3) Postgres
        conn = psycopg2.connect(
            dbname=os.getenv("DB_POSTGRES_DB_NAME"),
            user=os.getenv("DB_POSTGRES_USERNAME"),
            password=os.getenv("DB_POSTGRES_PASSWORD"),
            host=os.getenv("DB_POSTGRES_HOST"),
            port=os.getenv("DB_POSTGRES_PORT"),
        )

        # 4) Loop companies & years
        for sec in companies:
            doc = mongo.get_report_by_company(sec)
            if not doc:
                continue

            years = [args.year] if args.year else mongo.get_available_years(doc)
            if args.year and args.company is None:
                logger.warning("--year requires --company; ignoring year filter.")
                years = mongo.get_available_years(doc)

            if not years:
                logger.warning(f"No parsed years for {sec}; skipping.")
                continue

            # rebuild Document pages once per company
            pages = [Document(**p) for p in doc["report"]]
            index = VectorStoreIndex.from_documents(pages, embed_model=embed)
            qe = index.as_query_engine(similarity_top_k=10, llm=llm)

            for yr in years:
                logger.info(f"▶ {sec} / {yr}")
                prompt = ESG_PROMPT.format(company=sec, year=yr)
                rsp = qe.query(prompt)
                raw = getattr(rsp, "response", None) or rsp.response_text

                try:
                    metrics = parse_and_strip_json(raw)
                except json.JSONDecodeError:
                    logger.error(f"Invalid JSON for {sec}/{yr}; skipping.")
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

                with conn.cursor() as cur:
                    upsert_many(cur, "emissions", emissions)
                    upsert_many(cur, "energy",    energy)
                    upsert_many(cur, "waste",     waste)
                conn.commit()
                logger.success(f"Persisted {sec}/{yr} → Postgres.")

    conn.close()
    logger.success("✅ All done.")


if __name__ == "__main__":
    main()
