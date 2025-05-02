# -*- coding: utf-8 -*-
"""
┌──────────────────────────────────────────────────────────────────────────────┐
│ Main entry point for Coursework-2  ‖  课程二 CLI 主入口                       │
└──────────────────────────────────────────────────────────────────────────────┘
Features
1. extract          –  Extract & standardise metrics from a local PDF or MinIO object
2. convert          –  Flatten the final JSON into CSV
3. show-catalogue   –  Display the CSR Data-Catalogue (CSV)
4. save-catalogue   –  Persist the catalogue into MongoDB
5. show-dictionary  –  Print the field-level Data-Dictionary
6. show-lineage     –  Show the latest 5 pipeline lineage records
7. ingest           –  Ingest a final JSON into MongoDB
8. show-report      –  Query an ingested report by company_id / year
"""

import sys
import os
import time
import argparse
from pathlib import Path
from typing import Optional, Dict, Any
import json
import pandas as pd


# ─── Internal imports  内部模块 ────────────────────────────────────────────────
from modules.extract.config_loader import (
    OUTPUT_DIR,
    PDF_PATH,
    PDF_OBJECT_KEY,
    DATA_DICT,
    FINAL_JSON,
    OUTPUT_PDF,
    OUTPUT_MD,
    OUTPUT_JSON,
    OUTPUT_CSV,
)
from modules.extract.minio_client         import download_pdf
from modules.extract.extractor            import main as extract_main, refine_extracted
from modules.extract.utils                import convert_json_to_csv
from modules.extract.catalogue_loader     import load_catalogue
from modules.db.mongo_operations  import save_catalogue_to_mongo
from modules.db.lineage           import record_lineage
from modules.db.ingest            import ingest_report
from modules.db.query             import fetch_report
from modules.extract.company_lookup import get_company_id
from modules.extract.batch import run_batch
from modules.extract.minio_client import list_objects
from modules.Viz.app import app as viz_app
from modules.logging_config import setup_logging


setup_logging(os.getenv("LOG_LEVEL", "INFO"))
# ──────────────────────────────────────────────────────────────────────────────
# Helper – context-manager timer  简易计时器
# ──────────────────────────────────────────────────────────────────────────────
class Timer:
    def __enter__(self):
        self.t0 = time.perf_counter()
        return self

    def __exit__(self, *exc):
        self.elapsed = time.perf_counter() - self.t0


# ──────────────────────────────────────────────────────────────────────────────
# 1) extract command  抽取并标准化
# ──────────────────────────────────────────────────────────────────────────────
import re
import json
import argparse
from pathlib import Path
from typing import Any, Dict, Optional

from modules.db.ingest import ingest_report
from modules.extract.company_lookup import get_company_id
from modules.extract.extractor import main as extract_main, refine_extracted_data as refine_extracted
from modules.extract.minio_client        import download_pdf
from modules.db.lineage            import record_lineage

from modules.extract.config_loader import PDF_PATH, PDF_OBJECT_KEY, OUTPUT_DIR, OUTPUT_PDF, OUTPUT_MD, OUTPUT_CSV


def extract_command(args: argparse.Namespace) -> None:
    """extract → pass-1 extraction & pass-2 refinement"""
    # —— Determine PDF source ——
    if args.minio_key:
        key = args.minio_key
    elif PDF_OBJECT_KEY:
        key = PDF_OBJECT_KEY
    else:
        key = None

    if key:
        local_pdf = OUTPUT_DIR / key.replace("/", "_")
        print(f"⏬  Downloading {key} from MinIO → {local_pdf}")
        pdf_path = download_pdf(key, local_pdf)
    else:
        pdf_path = Path(args.pdf or PDF_PATH)
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")

    # —— Pass-1 extraction ——
    print("🚀  Starting first-pass extraction …")
    with Timer() as t1:
        raw_json: Optional[Path] = extract_main(str(pdf_path))

    if not raw_json or not raw_json.exists():
        print("❌  First pass failed or produced no output.")
        return
    print(f"✅  First pass finished in {t1.elapsed:.1f}s  →  {raw_json}")

    # —— Pass-2 refinement ——
    print("🛠   Starting second-pass standardisation …")
    with Timer() as t2:
        final_json = refine_extracted(raw_json, OUTPUT_DIR)

    if not final_json or not Path(final_json).exists():
        print("⚠️   Second pass produced no data.")
        return
    print(f"✅  Second pass finished in {t2.elapsed:.1f}s  →  {final_json}")

    # —— 解析 company_id & display_name —— 
    display_name = Path(args.minio_key or pdf_path.name).stem
    company_id   = get_company_id(display_name)

    # —— 智能解析 report_year —— 
    report_year: Optional[int] = None
    if args.minio_key:
        first = args.minio_key.split('/', 1)[0]
        if first.isdigit():
            report_year = int(first)

    if report_year is None:
        m = re.search(r'\b(19|20)\d{2}\b', display_name)
        if m:
            report_year = int(m.group())

    print(f"🏷️  company_id = {company_id}  ({display_name})")
    print(f"📅  report_year = {report_year}")

    # —— 注入 company_name 和 report_year 到 final JSON —— 
    with open(final_json, "r", encoding="utf-8") as f:
        data: Dict[str, Any] = json.load(f)

    for theme_items in data.values():
        for rec in theme_items:
            rec["company_name"] = display_name
            if report_year is not None:
                rec["report_year"] = report_year

    with open(final_json, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    # —— 记录谱系 —— 
    run_stats: Dict[str, Any] = {
        "run_seconds": round(t1.elapsed + t2.elapsed, 2),
    }
    outputs: Dict[str, str] = {
        "filtered_pdf": str(OUTPUT_DIR / OUTPUT_PDF),
        "markdown":     str(OUTPUT_DIR / OUTPUT_MD),
        "raw_json":     str(raw_json),
        "final_json":   str(final_json),
        "csv":          str(OUTPUT_DIR / OUTPUT_CSV),
    }
    record_lineage(
        pdf_src          = key or str(pdf_path),
        stats            = run_stats,
        outputs          = outputs,
        pipeline_version = "v0.1.0",
    )

    # —— Auto-ingest —— 
    print(f"💾  Ingesting into MongoDB → company_id={company_id}")
    ingest_report(Path(final_json), company_id)
    print("✅  Ingestion complete.")





# ──────────────────────────────────────────────────────────────────────────────
# 2) convert command  JSON → CSV
# ──────────────────────────────────────────────────────────────────────────────
def convert_command(args: argparse.Namespace) -> None:
    json_p = Path(args.json_file)
    csv_p  = Path(args.csv_file)
    print(f"🔄  Converting {json_p} → {csv_p}")
    ok = convert_json_to_csv(json_p, csv_p)
    print("✅  CSV conversion succeeded." if ok else "❌  CSV conversion failed.")


# ──────────────────────────────────────────────────────────────────────────────
# 3) show-catalogue command  展示 Catalogue
# ──────────────────────────────────────────────────────────────────────────────
def show_catalogue_command(_: argparse.Namespace) -> None:
    print("📖  Loading CSR Data-Catalogue …")
    df = load_catalogue()
    print(df.head(20).to_string(index=False))


# ──────────────────────────────────────────────────────────────────────────────
# 4) save-catalogue command  Catalogue → MongoDB
# ──────────────────────────────────────────────────────────────────────────────
def save_catalogue_command(_: argparse.Namespace) -> None:
    print("💾  Saving catalogue into MongoDB …")
    ok = save_catalogue_to_mongo()
    print("✅  Catalogue saved." if ok else "❌  Failed to save catalogue.")


# ──────────────────────────────────────────────────────────────────────────────
# 5) show-dictionary command  打印 Data-Dictionary
# ──────────────────────────────────────────────────────────────────────────────
def show_dictionary_command(_: argparse.Namespace) -> None:
    print("📋  Data-Dictionary\n")
    df = pd.DataFrame.from_dict(DATA_DICT, orient="index").reset_index()
    df = df.rename(columns={"index": "field"})
    print(df.to_string(index=False))


# ──────────────────────────────────────────────────────────────────────────────
# 6) show-lineage command  最近 5 条 lineage
# ──────────────────────────────────────────────────────────────────────────────
def show_lineage_command(_: argparse.Namespace) -> None:
    from pymongo import MongoClient
    from modules.extract.config_loader import database
    client = MongoClient(database["mongo_uri"])
    coll   = client[database["mongo_db"]]["csr_lineage"]
    docs   = list(coll.find().sort("timestamp", -1).limit(5))
    print("📑  Latest 5 pipeline lineage records")
    print(json.dumps(
        [{k: v for k, v in d.items() if k != "_id"} for d in docs],
        indent=2, ensure_ascii=False
    ))


# ──────────────────────────────────────────────────────────────────────────────
# 7) ingest command  单独入库
# ──────────────────────────────────────────────────────────────────────────────
def ingest_command(args: argparse.Namespace) -> None:
    json_p = Path(args.json_file or OUTPUT_DIR / FINAL_JSON)
    if not json_p.exists():
        print(f"❌  JSON file not found: {json_p}")
        return
    print(f"💾  Ingesting {json_p} into MongoDB …")
    ingest_report(json_p)
    print("✅  Ingestion complete.")


# ──────────────────────────────────────────────────────────────────────────────
# 8) show-report command  查询报告
# ──────────────────────────────────────────────────────────────────────────────
def show_report_command(args: argparse.Namespace) -> None:
    print(f"🔍  Querying company_id={args.company_id}"
          f"{', year=' + str(args.report_year) if args.report_year else ''}")
    doc = fetch_report(args.company_id, args.report_year)
    if not doc:
        print("⚠️  No report matched your query.")
        return
    print(json.dumps(doc, indent=2, ensure_ascii=False))


def serve_command(args: argparse.Namespace) -> None:
    """
    Serve the Flask-based dashboard from modules/viz/app.py
    """
    host = args.host
    port = args.port
    print(f"🔧  Starting Flask dashboard at http://{host}:{port}/")
    # 这里直接调用 Flask app.run
    viz_app.run(host=host, port=port, debug=True)


# ──────────────────────────────────────────────────────────────────────────────
# CLI builder  CLI 构筑
# ──────────────────────────────────────────────────────────────────────────────
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Coursework-2 ESG Data CLI  |  课程二 ESG 数据命令行工具"
    )
    sub = parser.add_subparsers(dest="cmd", help="sub-commands")

    # extract
    p_ex = sub.add_parser("extract", help="Extract & standardise")
    p_ex.add_argument("--pdf", type=str, help="Local PDF path")
    p_ex.add_argument("--minio-key", dest="minio_key", type=str,
                      help="MinIO object key (e.g. reports/2024.pdf)")
    p_ex.set_defaults(func=extract_command)

    # convert
    p_cv = sub.add_parser("convert", help="JSON → CSV")
    p_cv.add_argument("--json_file", default=str(OUTPUT_DIR / FINAL_JSON),
                      help="Input JSON path")
    p_cv.add_argument("--csv_file",  default=str(OUTPUT_DIR / OUTPUT_CSV),
                      help="Output CSV path")
    p_cv.set_defaults(func=convert_command)

    # show-catalogue
    sub.add_parser("show-catalogue", help="Display CSR Data-Catalogue") \
       .set_defaults(func=show_catalogue_command)

    # save-catalogue
    sub.add_parser("save-catalogue", help="Save catalogue to MongoDB") \
       .set_defaults(func=save_catalogue_command)

    # show-dictionary
    sub.add_parser("show-dictionary", help="Display Data-Dictionary") \
       .set_defaults(func=show_dictionary_command)

    # show-lineage
    sub.add_parser("show-lineage", help="Display latest 5 lineage records") \
       .set_defaults(func=show_lineage_command)

    # ingest
    p_ing = sub.add_parser("ingest", help="Ingest a final JSON into MongoDB")
    p_ing.add_argument("--json_file", type=str,
                       default=str(OUTPUT_DIR / FINAL_JSON),
                       help="JSON file to ingest (default: final_standardized.json)")
    p_ing.set_defaults(func=ingest_command)

    # show-report
    p_sr = sub.add_parser("show-report", help="Query one ingested report")
    p_sr.add_argument("--company_id", type=int, required=True,
                      help="Company ID (required)")
    p_sr.add_argument("--year", dest="report_year", type=int, default=None,
                      help="Report year (optional)")
    p_sr.set_defaults(func=show_report_command)


    # batch-extract
    p_be = sub.add_parser("batch-extract", help="Extract whole MinIO bucket (or prefix)")
    p_be.add_argument("--prefix", type=str, default=None,
                      help="Only process keys that start with this prefix, e.g. '2024/'")
    p_be.add_argument("--limit", type=int, default=None,
                      help="Process first N files only (debug)")
    p_be.set_defaults(func=lambda a: run_batch(a.prefix, a.limit))


    # serve Flask dashboard
    p_sv = sub.add_parser("serve", help="Run the Flask visualization dashboard")
    p_sv.add_argument("--host", default="0.0.0.0", help="Flask host")
    p_sv.add_argument("--port", type=int, default=5000, help="Flask port")
    p_sv.set_defaults(func=serve_command)


    return parser



# ──────────────────────────────────────────────────────────────────────────────
# main entry  主函数入口
# ──────────────────────────────────────────────────────────────────────────────
def main() -> int:
    parser = build_parser()
    args   = parser.parse_args()

    if not hasattr(args, "func"):
        parser.print_help()
        return 1

    try:
        args.func(args)
        return 0
    except Exception as exc:
        print(f"💥  Error: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
