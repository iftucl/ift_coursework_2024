# modules/pipeline.py
from Main import extract_main, refine_extracted, OUTPUT_DIR
def run_pipeline_for_pdf(key: str, bucket: str = "csr-reports") -> None:
    """
    key = "2024/Apple Inc..pdf"
    """
    try:
        # —— 下载到本地 —— 
        local_pdf = OUTPUT_DIR / key.replace("/", "_")
        pdf_path  = download_pdf(key, local_pdf, bucket=bucket)  # 你已有的 download_pdf
        # —— Pass-1 / Pass-2 —— 
        raw_json  = extract_main(str(pdf_path))
        final_json = refine_extracted(raw_json, OUTPUT_DIR)
        # —— Ingest —— 
        ingest_report(Path(final_json))
        print(f"[OK] done → {key}")
    except Exception as e:
        print(f"[ERROR] {key} failed – {e}")