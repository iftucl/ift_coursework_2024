"""
封装单 PDF → 标准化 → 入库，以及批量调度
"""
from pathlib import Path
from typing import Optional, Dict, Any, List
import json, re, time

from modules.extract.minio_client   import download_pdf, list_objects
from modules.extract.extractor      import main as extract_main, refine_extracted_data as refine_extracted
from modules.db.ingest      import ingest_report
from modules.db.lineage     import record_lineage
from modules.extract.company_lookup import get_company_id
from modules.extract.config_loader  import OUTPUT_DIR, OUTPUT_PDF, OUTPUT_MD, OUTPUT_CSV


# ──────────────────────────────────────────────────────────────
# 小工具：计时器
# ──────────────────────────────────────────────────────────────
class Timer:
    def __enter__(self): self.t0 = time.perf_counter(); return self
    def __exit__(self, *exc): self.elapsed = time.perf_counter() - self.t0


# ──────────────────────────────────────────────────────────────
# 单文件流水线
# ──────────────────────────────────────────────────────────────
def run_single(key: str) -> bool:
    """
    处理 MinIO 里的一个 PDF（object key）。
    成功返回 True，失败 False（不会抛异常，方便批量循环）。
    """
    try:
        local_pdf = OUTPUT_DIR / key.replace("/", "_")
        print(f"\n⏬  [{key}] Downloading → {local_pdf}")
        pdf_path  = download_pdf(key, local_pdf)

        # —— 第一遍抽取 ——
        with Timer() as t1:
            raw_json = extract_main(str(pdf_path))
        if not raw_json or not Path(raw_json).exists():
            print(f"❌  [{key}] first-pass extraction failed")
            return False

        # —— 第二遍标准化 ——
        with Timer() as t2:
            final_json = refine_extracted(raw_json, OUTPUT_DIR)
        if not final_json or not Path(final_json).exists():
            print(f"⚠️   [{key}] second-pass produced no data")
            return False

        # —— 填充元数据（company / report_year） ——
        display_name = Path(key).stem
        company_id   = get_company_id(display_name)

        report_year: Optional[int] = None
        first_seg = key.split('/', 1)[0]
        if first_seg.isdigit():
            report_year = int(first_seg)
        if report_year is None:
            m = re.search(r'\b(19|20)\d{2}\b', display_name)
            if m:
                report_year = int(m.group())

        with open(final_json, "r", encoding="utf-8") as f:
            data: Dict[str, Any] = json.load(f)

        for items in data.values():
            for rec in items:
                rec["company_name"] = display_name
                if report_year:
                    rec["report_year"] = report_year

        with open(final_json, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        # —— 入库 & lineage —— 
        ingest_report(Path(final_json), company_id)
        record_lineage(
            pdf_src=key,
            stats={"run_seconds": round(t1.elapsed + t2.elapsed, 2)},
            outputs={
                "filtered_pdf": str(OUTPUT_DIR / OUTPUT_PDF),
                "markdown":     str(OUTPUT_DIR / OUTPUT_MD),
                "raw_json":     str(raw_json),
                "final_json":   str(final_json),
                "csv":          str(OUTPUT_DIR / OUTPUT_CSV),
            },
            pipeline_version="v0.1.0",
        )
        print(f"✅  [{key}] done")
        return True

    except Exception as e:
        print(f"💥  [{key}] error: {e}")
        return False


# ──────────────────────────────────────────────────────────────
# 批量调度
# ──────────────────────────────────────────────────────────────
def run_batch(prefix: Optional[str] = None, limit: Optional[int] = None):
    """
    批量处理整个 MinIO 存储桶（或指定前缀）里的 PDF。
    prefix : 只处理以该前缀开头的对象（如 "2024/"）
    limit  : 仅处理前 N 个（调试用）
    """
    # 1. 列举 + 再去重
    keys: List[str] = sorted(set(list_objects(prefix)), key=str.lower)
    if limit:
        keys = keys[:limit]

    print(f"🗂   Total {len(keys)} PDF to process.")
    ok = fail = 0

    # 2. 顺序处理
    for k in keys:
        if run_single(k):
            ok += 1
        else:
            fail += 1

    print(f"\n🥳  Batch finished → success={ok}, fail={fail}")
