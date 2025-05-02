# modules/db/ingest.py
from __future__ import annotations

from pathlib import Path
from datetime import datetime
import json, re, ast, operator as op
from typing import Dict, List, Any, Union

from pymongo import MongoClient
from bson import ObjectId

# ─── Legacy dependencies (Mongo / validation / dimension table) ───
from modules.extract.config_loader  import MONGO_URI, MONGO_DB
from modules.extract.validator      import validate_record
from modules.extract.company_lookup import get_company_id

# ─── New: lightweight PostgreSQL DAO  (see modules/db/pg_client.py) ─
from modules.db.pg_client import (                         # type: ignore
    _upsert_company as pg_upsert_company,
    _upsert_indicator as pg_upsert_indicator,
    batch_insert_metrics,
    batch_insert_targets,
)

# ───────────────────────── Constants ─────────────────────────
_THEMATIC = {
    "GHG Emissions": "Environment", "Energy": "Environment",
    "Water": "Environment", "Operational Waste": "Environment",
    "Product Sustainability & Circularity": "Environment",
    "Social": "Social", "Governance": "Governance",
}
_CUR_YEAR = datetime.utcnow().year
_SLUG_RE  = re.compile(r"[^a-z0-9]+", re.I)     # generate indicator_id
_NUM_RE   = re.compile(r"-?\d+(?:\.\d+)?")      # extract first numeric value

SAFE_OP = {
    ast.Add:  op.add,    ast.Sub:  op.sub,
    ast.Mult: op.mul,    ast.Div:  op.truediv,
    ast.Pow:  op.pow,    ast.USub: op.neg,
}

# ──────────────────────── Utility functions ───────────────────────
def _mongo_col(name: str = "csr_reports"):
    return MongoClient(MONGO_URI)[MONGO_DB][name]


def _safe_eval(expr: str) -> Union[float, None]:
    """Parse a simple arithmetic expression (digits only); return None on failure"""
    try:
        tree = ast.parse(expr, mode="eval").body

        def _eval(node):
            if isinstance(node, ast.Num):
                return node.n
            if isinstance(node, ast.BinOp):
                return SAFE_OP[type(node.op)](_eval(node.left), _eval(node.right))
            if isinstance(node, ast.UnaryOp):
                return SAFE_OP[type(node.op)](_eval(node.operand))
            raise ValueError

        return float(_eval(tree))
    except Exception:
        return None


def _num_from_str(txt: str) -> Union[float, None]:
    """'≈ 1,234' / '–' → 1234.0 / None; try eval first, then regex"""
    if not isinstance(txt, str):
        return None
    val = _safe_eval(txt.replace(" ", ""))
    if val is not None:
        return val
    m = _NUM_RE.search(txt.replace(",", ""))
    return float(m.group()) if m else None


def _clean_numeric(rec: Dict[str, Any], field: str):
    """Handle list or scalar values"""
    v = rec.get(field)
    if isinstance(v, list):
        rec[field] = [
            x if isinstance(x, (int, float)) else _num_from_str(str(x)) for x in v
        ]
    elif isinstance(v, str):
        rec[field] = _num_from_str(v)


def _first(v):
    """Return the first element of a list or the original value"""
    if isinstance(v, list):
        return v[0] if v else None
    return v


# ───────────────────────── Main function ────────────────────────
def ingest_report(
    json_path: Path, company: Union[str, ObjectId, None] = None
) -> None:

    # ① File check
    if not isinstance(json_path, Path):
        raise TypeError("json_path must be pathlib.Path")
    if not json_path.exists():
        raise FileNotFoundError(json_path)

    # ② Resolve company (Mongo dimension + PostgreSQL company_dim)
    db = MongoClient(MONGO_URI)[MONGO_DB]
    comp_col = db.dim_companies
    if isinstance(company, ObjectId):
        company_id = company
        company_name = (comp_col.find_one({"_id": company_id}) or {}).get("name")
    else:
        company_name = (
            company.strip()
            if isinstance(company, str) and company.strip()
            else json_path.stem.split("_", 1)[-1]
        )
        company_id = get_company_id(company_name)
    if company_id is None:
        print(f"[ERROR] Unable to resolve company_id (name={company_name!r})")
        return
    print(f"💾  Ingesting → {company_name} ({company_id})")

    # —— PostgreSQL dimension upsert — returns integer PK
    pg_company_id = pg_upsert_company(company_name.lower(), company_name)

    # ③ Read JSON
    raw: Dict[str, List[Dict[str, Any]]] = json.loads(json_path.read_text("utf-8"))

    # ④ Build records (prepare PG rows simultaneously)
    recs: List[Dict[str, Any]] = []
    metric_rows_pg: List[dict] = []
    target_rows_pg: List[dict] = []

    indicator_cache: Dict[str, int] = {}  # slug → indicator_id (PG)

    for theme, rows in raw.items():
        for row in rows:
            r = dict(row)  # shallow copy
            r["thematic_area"] = _THEMATIC.get(theme, theme)

            # —— Metadata ——
            r.update(
                {
                    "company_id": company_id,
                    "company_name": company_name,
                    "ingested_at": datetime.utcnow(),
                    "sub_category": r.get("sub_category")
                    or r.get("indicator_name")
                    or "N/A",
                }
            )
            if not r.get("indicator_id"):
                r["indicator_id"] = (
                    _SLUG_RE.sub("_", (r.get("indicator_name") or "").lower())
                    .strip("_")
                    or "unknown"
                )

            # report_year
            if r.get("report_year") is None:
                try:
                    r["report_year"] = int(json_path.stem.split("_", 1)[0])
                except Exception:
                    pass

            # indicator_year (metrics only)
            if r.get("record_type") != "target":
                if r.get("indicator_year") is None:
                    yrs = r.get("years")
                    yr = None
                    if isinstance(yrs, int):
                        yr = yrs
                    elif isinstance(yrs, list):
                        ints = [y for y in yrs if isinstance(y, int)]
                        yr = min(ints) if ints else None
                    yr = yr or r.get("baseline_year") or r.get("report_year")
                    if isinstance(yr, int):
                        r["indicator_year"] = yr
            else:
                # target → remove indicator_year to avoid future-year validation errors
                r.pop("indicator_year", None)

            # record_type fallback
            if not r.get("record_type"):
                r["record_type"] = (
                    "target"
                    if r.get("goal_text") or r.get("target_value") is not None
                    else "metric"
                )

            # Clean numeric fields
            _clean_numeric(r, "values_numeric")
            _clean_numeric(r, "target_value")

            # —— PostgreSQL dimension: indicator_dim (cache to avoid duplicate upsert)
            slug = r["indicator_id"]
            if slug not in indicator_cache:
                indicator_cache[slug] = pg_upsert_indicator(
                    slug=slug,
                    name=r.get("indicator_name") or slug,
                    area=r["thematic_area"],
                )
            pg_indicator_id = indicator_cache[slug]

            # —— Pre-build PG rows (does not affect old logic) ——
            if r["record_type"] == "metric":
                metric_rows_pg.append(
                    {
                        "company_id": pg_company_id,
                        "indicator_id": pg_indicator_id,
                        "report_year": r.get("report_year"),
                        "indicator_year": r.get("indicator_year"),
                        "value_numeric": _first(r.get("values_numeric")),
                        "value_text": _first(r.get("values_text")),
                        "unit": r.get("unit"),
                        "page_number": r.get("page_number"),
                        "source": r.get("source"),
                    }
                )
            else:  # target / commitment
                target_rows_pg.append(
                    {
                        "company_id": pg_company_id,
                        "indicator_id": pg_indicator_id,
                        "goal_text": r.get("goal_text"),
                        "progress_text": r.get("progress_text"),
                        "baseline_year": r.get("baseline_year"),
                        "target_year": r.get("target_year"),
                        "target_value": r.get("target_value"),
                        "target_unit": r.get("target_unit"),
                        "page_number": r.get("page_number"),
                        "source": r.get("source"),
                    }
                )

            recs.append(r)

    # ⑤ Validation & write to MongoDB (old logic intact)
    col = _mongo_col()
    ok = bad = 0

    for r in recs:
        try:
            validate_record(r)
        except ValueError as e:
            # Clean again and retry (specifically for could-not-convert)
            if "convert string to float" in str(e):
                _clean_numeric(r, "values_numeric")
                _clean_numeric(r, "target_value")
                try:
                    validate_record(r)
                except Exception:
                    pass
            else:
                bad += 1
                print(f"[WARN] Validation failed, skipped – {e}")
                continue

        col.insert_one(r)
        ok += 1

    # ⑥ Batch write to PostgreSQL
    try:
        batch_insert_metrics(metric_rows_pg)
        batch_insert_targets(target_rows_pg)
        print(
            f"[RESULT] Mongo inserted {ok}, skipped {bad}  |  "
            f"PostgreSQL metrics={len(metric_rows_pg)}, targets={len(target_rows_pg)}"
        )
    except Exception as e:
        print(f"[ERROR] PostgreSQL batch insert failed – {e}")
