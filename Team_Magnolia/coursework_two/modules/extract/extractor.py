"""
Sustainability Report Data Extractor  (Coursework‑2)
===================================================
PDF ➜ Markdown ➜ Pass‑1 extraction ➜ Pass‑2 refinement  
本模块完成 ESG 可持续报告的整套抽取与标准化流程。

Key design goals / 设计要点
--------------------------------
1. **Graceful fallback** – works even when regex filters miss all pages.
2. **Theme‑wise refinement** – smaller prompt → fewer 5xx / JSON errors.
3. **Clear logging** – English with minimal bilingual hints.

Usage
-----
```bash
python Main.py extract --pdf path/to/report.pdf
python Main.py extract --minio-key "2024/Apple.pdf"
```

Dependencies configured via `modules/config_loader.py`.
"""
from __future__ import annotations

import json, os, re, time, json5
from pathlib import Path
from collections import defaultdict
from typing import List, Dict, Any

import fitz                       # PyMuPDF
import torch
from openai import OpenAI
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import (
    PdfPipelineOptions,
    AcceleratorOptions,
    AcceleratorDevice,
    TableStructureOptions,
    TableFormerMode,
)

# ─── Internal config & prompts ─────────────────────────────────────────────
from modules.extract.config_loader import (
    OUTPUT_DIR, PDF_PATH,
    OUTPUT_PDF, OUTPUT_MD, OUTPUT_JSON,
    GROQ_API_KEY, GROQ_BASE_URL, GROQ_MODEL,
    PAGE_BREAK, YEAR_RE, THEMES,
)
from modules.extract.prompts import THEME_PROMPTS, REFINEMENT_PROMPT

FALLBACK_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"
# ──────────────────────────────────────────────────────────────────────────
# 0. Utilities
# ──────────────────────────────────────────────────────────────────────────

def _accelerator():
    """auto‑select MPS/CPU"""
    if torch.backends.mps.is_available() and torch.backends.mps.is_built():
        print("[Info] Using Apple MPS")
        return AcceleratorOptions(device=AcceleratorDevice.MPS, num_threads=4)
    print("[Info] Using CPU")
    return AcceleratorOptions(device=AcceleratorDevice.CPU, num_threads=4)


def _match_theme(text: str, cfg: dict) -> bool:
    """Return *True* if page text matches the theme config."""
    goal_hit = cfg.get("goal_kw_re") and all(p.search(text) for p in cfg["goal_kw_re"])
    if not goal_hit and cfg.get("unit_re") and not cfg["unit_re"].search(text):
        return False

    yrs = YEAR_RE.findall(text)
    if cfg.get("require_multiple_year_occurrences", False):
        if len(yrs) < 2:
            return False
    elif not yrs:
        return False

    if cfg.get("require_all_keywords", False):
        if not all(p.search(text) for p in cfg["keyword_re"]):
            return False
    else:
        hits = len({p.pattern for p in cfg["keyword_re"] if p.search(text)})
        if hits < cfg.get("min_keyword_hits", 1):
            return False

    if cfg.get("extra_re") and not any(p.search(text) for p in cfg["extra_re"]):
        return False
    return True


# ──────────────────────────────────────────────────────────────────────────
# 1. Page filtering
# ──────────────────────────────────────────────────────────────────────────

def filter_pdf(src: str | Path, dst: str | Path):
    selected, flags, labels = set(), defaultdict(list), {}
    with fitz.open(str(src)) as doc:
        for idx, pg in enumerate(doc):
            label_txt = pg.get_label()
            m = re.search(r"\d+", label_txt or "")
            labels[idx] = int(m.group()) if m else idx + 1
            text = pg.get_text("text") or ""
            for theme, cfg in THEMES.items():
                if _match_theme(text, cfg):
                    selected.add(idx)
                    flags[idx].append(theme)

        # fallback – use full PDF
        if not selected:
            print("[WARN] No page matched regex filters – using entire PDF")
            selected = set(range(len(doc)))
            for i in selected:
                flags[i] = ["ALL"]

        new = fitz.open()
        for i in sorted(selected):
            _ = new.new_page(width=doc[i].rect.width, height=doc[i].rect.height)
            _.show_pdf_page(_.rect, doc, i)
        Path(dst).parent.mkdir(parents=True, exist_ok=True)
        new.save(str(dst), garbage=4, deflate=True)
        print(f"[OK] Filtered PDF → {dst}  ({len(selected)} pages)")
    return dict(flags), sorted(selected), labels


# ──────────────────────────────────────────────────────────────────────────
# 2. PDF → Markdown (Docling + OCR)
# ──────────────────────────────────────────────────────────────────────────

def parse_with_docling(pdf: Path, orig_idx: List[int], labels: Dict[int, int], out_md: Path):
    pipeline = PdfPipelineOptions(
        do_ocr=True,
        ocr_languages=["eng"],
        do_table_structure=True,
        accelerator_options=_accelerator(),
        table_structure_options=TableStructureOptions(do_cell_matching=True, mode=TableFormerMode.FAST),
    )
    converter = DocumentConverter({InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline)})
    print("[Info] Running Docling + OCR …")
    doc = converter.convert(str(pdf)).document
    md_pages = doc.export_to_markdown(page_break_placeholder=PAGE_BREAK).split(PAGE_BREAK)

    def _mk(i):  # assemble with true page‑number
        disp = labels.get(orig_idx[i], orig_idx[i] + 1)
        return f"--- PAGE {disp} ---\n\n{md_pages[i].strip()}"

    merged: List[str] = [_mk(i) for i in range(min(len(md_pages), len(orig_idx)))]
    if len(md_pages) > len(orig_idx):  # extra split pages
        for i in range(len(orig_idx), len(md_pages)):
            merged.append(f"--- PAGE UNKNOWN ---\n\n{md_pages[i].strip()}")

    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text("\n\n".join(merged), encoding="utf-8")
    print(f"[OK] Markdown saved → {out_md}")
    return out_md


# ──────────────────────────────────────────────────────────────────────────
# 3. First‑pass LLM extraction
# ──────────────────────────────────────────────────────────────────────────

def _rough_tokens(txt: str) -> int:
    return len(txt) // 4 or 1

def _batches(pgs: List[int], md: str, max_toks: int = 10_000):
    cur, tok, out = [], 0, []
    for p in pgs:
        seg = grab_pages(md, [p])
        tks = _rough_tokens(seg)
        if cur and tok + tks > max_toks:
            out.append(cur)
            cur, tok = [], 0
        cur.append(p); tok += tks
    if cur:
        out.append(cur)
    return out


def grab_pages(md: str, pages: List[int]) -> str:
    parts = re.split(r"(?:^|\n\n)--- PAGE (\d+) ---\n\n", md)
    pg_map = {int(parts[i]): parts[i + 1] for i in range(1, len(parts), 2)}
    return "\n\n".join(f"--- PAGE {p} ---\n\n{pg_map.get(p, '')}" for p in pages)


def llm_extract(client: OpenAI, text: str, prompt: str, max_retry: int = 3):
    """
    Use Groq LLM to extract structured data from text, with retries & fallback.
    """
    if not text.strip():
        print("Skipping LLM call: Input text is empty.")
        return {}

    # 尝试顺序：先主模型，再备选模型
    for model_name in (GROQ_MODEL, FALLBACK_MODEL):
        for attempt in range(1, max_retry + 1):
            try:
                print(f"→ Calling model={model_name} (attempt {attempt}/{max_retry}), text len={len(text)}")
                resp = client.chat.completions.create(
                    model=model_name,
                    messages=[{"role": "system", "content": prompt},
                              {"role": "user",   "content": text}],
                    temperature=0.1,
                    response_format={"type": "json_object"},
                )
                raw = resp.choices[0].message.content
                # 解析 JSON
                try:
                    return json.loads(raw)
                except json.JSONDecodeError:
                    return json5.loads(raw)
            except Exception as e:
                code = getattr(e, 'status_code', None) or getattr(e, 'code', None)
                msg = getattr(e, 'message', str(e))
                print(f"[WARN] extract failure | model={model_name} ({attempt}/{max_retry}) → "
                      f"Error code: {code} - {msg}")
                # 对 503 类服务不可用做指数退避
                time.sleep(2 ** (attempt - 1))
        # 如果当前模型重试完了都不行，就切换到下一个
        print(f"[INFO] switching from {model_name} to next model")
    # 都失败了
    print("[ERROR] All models failed to extract; returning empty chunk")
    return {}
    


def extract_md(md: str, theme_pages: Dict[str, List[int]]) -> Dict[str, Any]:
    cli = OpenAI(api_key=GROQ_API_KEY, base_url=GROQ_BASE_URL)
    out: Dict[str, Any] = {}
    for theme, pages in theme_pages.items():
        for batch in _batches(pages, md):
            seg = grab_pages(md, batch)
            chunk = llm_extract(cli, seg, THEME_PROMPTS[theme])
            if chunk:
                out.setdefault(theme, {"reported_indicators": [], "commitments": []})
                for k in ("reported_indicators", "commitments"):
                    out[theme][k].extend(chunk.get(k, []))
    return out


# ──────────────────────────────────────────────────────────────────────────
# 4. Second‑pass refinement (theme‑wise) – helper
# ──────────────────────────────────────────────────────────────────────────

def _refine_theme(
    cli: OpenAI,
    theme: str,
    rows: List[Dict[str, Any]],
    retry: int = 3,
) -> List[Dict[str, Any]]:
    """
    • 先用首选模型；如 404/配额/JSON 校验出错 → 自动切换到下一个模型  
    • 每个模型各自重试 `retry` 次（指数退避 1,2,4…秒）  
    • 若全部模型都失败，则抛 RuntimeError 交给上层
    """
    # 按优先级排列；若没有访问权限会自动切到下一项
    model_chain = [
        "meta-llama/llama-4-maverick-17b-128e-instruct",
        "meta-llama/llama-4-scout-17b-16e-instruct",
        "llama-3.1-8b-instant",
    ]

    payload = json.dumps({theme: rows}, ensure_ascii=False)

    for model in model_chain:
        for attempt in range(1, retry + 1):
            try:
                resp = cli.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": REFINEMENT_PROMPT},
                        {"role": "user",   "content": payload},
                    ],
                    temperature=0.1,
                    response_format={"type": "json_object"},
                )
                raw = resp.choices[0].message.content

                # ── 严格解析 ─────────────────────────
                try:
                    return json.loads(raw)[theme]
                except json.JSONDecodeError:
                    # fallback: 宽松 JSON5 解析
                    return json5.loads(raw)[theme]

            except Exception as e:
                wait = 2 ** (attempt - 1)
                print(
                    f"[WARN] refine {theme} | model={model} "
                    f"({attempt}/{retry}) failed – retry in {wait}s → {e}"
                )
                time.sleep(wait)

        # 当前模型连失败 `retry` 次，换下一个
        print(f"[INFO] switching to fallback model → {model} ❌")

    # 所有模型都尝试过仍失败
    raise RuntimeError(f"refine {theme} failed on all fallback models")


# ──────────────────────────────────────────────────────────────────────────
# 5. Second‑pass refinement – public
# ──────────────────────────────────────────────────────────────────────────

def refine_extracted(raw_json: Path, out_dir: Path) -> Path | None:
    cli = OpenAI(api_key=GROQ_API_KEY, base_url=GROQ_BASE_URL)
    raw = json.loads(raw_json.read_text("utf-8"))
    if not any(raw.values()):
        print("[WARN] raw JSON empty → skip refinement")
        return None

    final: Dict[str, List[Dict[str, Any]]] = {}
    for theme, rows in raw.items():
        if not rows:
            continue
        try:
            final[theme] = _refine_theme(cli, theme, rows)
        except RuntimeError as e:
            print(f"[WARN] {e} – theme discarded")

    if not final:
        print("[WARN] all themes failed → no output")
        return None

    out_path = out_dir / "final_standardized.json"
    out_path.write_text(json.dumps(final, indent=2, ensure_ascii=False))
    print(f"[OK] final JSON → {out_path}")
    return out_path

# ──────────────────────────────────────────────────────────────────────────
# 6. Orchestrator (called from Main.py)
# ──────────────────────────────────────────────────────────────────────────

def main(pdf_path: str | Path | None = None):
    """End‑to‑end run. Return path to extracted_data.json"""
    pdf = Path(pdf_path or PDF_PATH)
    pdf.exists() or (_ := (_ for _ in ()).throw(FileNotFoundError(pdf)))

    OUT = Path(OUTPUT_DIR); OUT.mkdir(exist_ok=True)
    f_pdf, f_md, f_raw = OUT / OUTPUT_PDF, OUT / OUTPUT_MD, OUT / OUTPUT_JSON

    flags, sel_idx, labels = filter_pdf(pdf, f_pdf)

    # map theme → pages
    theme_pg = {
        t: sorted({labels.get(i, i + 1) for i, fl in flags.items() if t in fl}) for t in THEMES
    }
    if all(len(p) == 0 for p in theme_pg.values()):  # full fallback
        all_pg = [labels.get(i, i + 1) for i in sel_idx]
        theme_pg = {t: all_pg for t in THEMES}

    md_path = parse_with_docling(f_pdf, sel_idx, labels, f_md)
    if not md_path:
        return None

    md_txt = md_path.read_text("utf-8")
    raw_dict = extract_md(md_txt, theme_pg)
    f_raw.write_text(json.dumps(raw_dict, indent=2, ensure_ascii=False))
    print(f"[OK] raw JSON → {f_raw}")
    return f_raw

# When run standalone --------------------------------------------------------
if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser(description="Quick run extractor module")
    p.add_argument("pdf", nargs="?", default=None, help="PDF path override")
    p.add_argument("--refine", action="store_true", help="run second‑pass refinement")
    args = p.parse_args()

    raw_path = main(args.pdf)
    if args.refine and raw_path:
        refine_extracted(raw_path, OUTPUT_DIR)

# ---- put this at the very end of modules/extractor.py -----------------
# backward-compat: legacy call sites still import refine_extracted_data
refine_extracted_data = refine_extracted
