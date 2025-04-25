#!/usr/bin/env python3
"""
ingest_to_pg.py
===============

Query the **vector store** (built from parsed CSR reports), prompt **GPT-4**
to return nine key ESG indicators as JSON, then UPSERT them into three
PostgreSQL tables:

* ``emissions`` – Scope 1/2/3
* ``energy``     – energy + water metrics
* ``waste``      – waste + packaging metrics
"""

# ── standard library ──────────────────────────────────────────────────────
import argparse
import json
import os
import re
from pathlib import Path
from typing import Dict, List

# ── third-party ────────────────────────────────────────────────────────────
import psycopg2
from loguru import logger
from dotenv import load_dotenv
from llama_index.core import StorageContext, load_index_from_storage, VectorStoreIndex
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.llms.openai import OpenAI

load_dotenv()  # picks up OPENAI_API_KEY + DB creds from .env

# ── extraction prompt ------------------------------------------------------
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


# ── small helper -----------------------------------------------------------
def upsert_many(cur, table: str, rows: List[Dict]) -> None:
    """
    Bulk-UPSERT *rows* into *table* (``indicator_id`` is primary-key).

    Parameters
    ----------
    cur : psycopg2.extensions.cursor
        Active DB cursor.
    table : str
        Destination table name (``emissions`` | ``energy`` | ``waste``).
    rows : list[dict]
        Parsed JSON rows from GPT-4.
    """
    if not rows:
        return
    cols = list(rows[0])
    cols_csv = ", ".join(cols)
    placeholders = ", ".join(["%s"] * len(cols))
    updates = ", ".join(f"{c}=EXCLUDED.{c}" for c in cols if c != "indicator_id")

    sql = (
        f"INSERT INTO {table} ({cols_csv}) VALUES ({placeholders}) "
        f"ON CONFLICT (indicator_id) DO UPDATE SET {updates};"
    )
    cur.executemany(sql, [tuple(r[c] for c in cols) for r in rows])


# ── main pipeline ----------------------------------------------------------
def main() -> None:
    """
    CLI entrypoint.  
    Example::

        poetry run python ingest_to_pg.py --company Amazon --year 2023
    """
    # 1 ⎯ CLI args ----------------------------------------------------------
    ap = argparse.ArgumentParser(description="Extract ESG KPIs into Postgres")
    ap.add_argument("--company", required=True)
    ap.add_argument("--year", type=int, required=True)
    ap.add_argument("--persist_dir", type=Path, default=Path("data/vector_db"))
    ap.add_argument("--model_name", default="all-MiniLM-L6-v2")
    ap.add_argument("--openai_model", default="gpt-4o-mini")
    ap.add_argument("--openai_key", default=os.getenv("OPENAI_API_KEY"))
    args = ap.parse_args()

    # 2 ⎯ reload vector index ----------------------------------------------
    embed = HuggingFaceEmbedding(model_name=args.model_name)
    storage = StorageContext.from_defaults(persist_dir=str(args.persist_dir))
    index: VectorStoreIndex = load_index_from_storage(storage, embed_model=embed)

    # 3 ⎯ GPT-4 query -------------------------------------------------------
    llm = OpenAI(model=args.openai_model, api_key=args.openai_key)
    qe = index.as_query_engine(similarity_top_k=10, llm=llm)

    logger.info("Querying GPT-4 for structured ESG data …")
    rsp = qe.query(ESG_PROMPT.format(company=args.company, year=args.year))
    raw = getattr(rsp, "response", None) or rsp.response_text

    # strip ```json … ``` fences (GPT sometimes wraps output)
    clean = re.sub(r"^```json\s*|\s*```$", "", raw.strip(),
                   flags=re.IGNORECASE | re.DOTALL)

    try:
        metrics: List[Dict] = json.loads(clean)
    except json.JSONDecodeError as exc:
        logger.error("GPT-4 did not return valid JSON")
        logger.error(raw)
        raise exc

    # 4 ⎯ bucket rows -------------------------------------------------------
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

    # 5 ⎯ Postgres upsert ---------------------------------------------------
    conn = psycopg2.connect(
        dbname=os.getenv("DB_POSTGRES_DB_NAME", "fift"),
        user=os.getenv("DB_POSTGRES_USERNAME", "postgres"),
        password=os.getenv("DB_POSTGRES_PASSWORD", "postgres"),
        host=os.getenv("DB_POSTGRES_HOST", "localhost"),
        port=os.getenv("DB_POSTGRES_PORT", "5439"),
    )
    with conn, conn.cursor() as cur:
        upsert_many(cur, "emissions", emissions)
        upsert_many(cur, "energy",    energy)
        upsert_many(cur, "waste",     waste)

    logger.success("Done! ESG metrics persisted to Postgres.")


if __name__ == "__main__":  # pragma: no cover
    main()
