import nltk

import time
import sys
import os
import re
import json
import hashlib
from io import BytesIO
from typing import Dict, Any, List

import fitz  # PyMuPDF
from minio import Minio
from minio.error import S3Error
import psycopg2
from psycopg2.extras import Json
from nltk.tokenize import sent_tokenize
from tqdm import tqdm

nltk.download("punkt", quiet=True)

# -----------------------------------------------------------------------------
# Regex patterns
# -----------------------------------------------------------------------------
field_patterns = {
    "scope_1_emissions": { # 字段名
        "keywords": ["Scope 1", "Direct GHG emissions"], # 记录该字段可能在文本中出现的常见描述
        "regex": r"(?:Scope\s*1[^0-9a-zA-Z]{0,15})[:\-]?\s*(\d{1,3}(?:[ ,]?\d{3})*(?:\.\d+)?)(?=\s*(tCO2[e]?\b|tons|tonnes)?)"
    }, # 会去匹配 Scope 1 后面跟着的数字
    "scope_2_emissions": {
        "keywords": ["Scope 2", "Indirect emissions"],
        "regex": r"(?:Scope\s*2[^0-9a-zA-Z]{0,15})[:\-]?\s*(\d{1,3}(?:[ ,]?\d{3})*(?:\.\d+)?)(?=\s*(tCO2[e]?\b|tons|tonnes)?)"
    },
    "scope_3_emissions": {
        "keywords": ["Scope 3", "Other indirect emissions"],
        "regex": r"(?:Scope\s*3[^0-9a-zA-Z]{0,15})[:\-]?\s*(\d{1,3}(?:[ ,]?\d{3})*(?:\.\d+)?)(?=\s*(tCO2[e]?\b|tons|tonnes)?)"
    },
    "ghg_intensity": {
        "keywords": ["GHG intensity", "emission intensity"],
        "regex": r"(?:GHG|emission)\s+intensity[^0-9]{0,15}[:\-]?\s*(\d+(?:\.\d+)?)"
    },
    "total_energy": {
        "keywords": ["Total energy", "Energy consumption"],
        "regex": r"Total energy[^0-9]{0,20}?(\d{1,3}(?:[ ,]?\d{3})*(?:\.\d+)?)(?: ?(GJ|MWh|kWh))?"
    },
    "renewable_energy_share": {
        "keywords": ["Renewable energy", "% renewable"],
        "regex": r"(?:renewable[^0-9%]{0,15})[:\-]?\s*(\d{1,3}(?:\.\d+)?)\s?%"
    },
    "energy_intensity": {
        "keywords": ["Energy intensity"],
        "regex": r"(?:energy\s+intensity)[^0-9]{0,15}[:\-]?\s*(\d+(?:\.\d+)?)"
    },
    "total_water_withdrawal": {
        "keywords": ["Water withdrawal", "Total water"],
        "regex": r"(?:water\s+withdrawal|total\s+water)[^0-9]{0,15}[:\-]?\s*(\d{1,3}(?:[ ,]?\d{3})*(?:\.\d+)?)"
    },
    "water_consumption": {
        "keywords": ["Water consumption"],
        "regex": r"(?:water\s+consumption)[^0-9]{0,15}[:\-]?\s*(\d{1,3}(?:[ ,]?\d{3})*(?:\.\d+)?)"
    },
    "water_reused_share": {
        "keywords": ["Water reused", "% reused", "water recycling"],
        "regex": r"(?:reused|recycling)[^0-9%]{0,10}[:\-]?\s*(\d{1,3}(?:\.\d+)?)\s?%"
    },
    "total_plastic_usage": {
        "keywords": ["Total plastic", "Plastic usage"],
        "regex": r"(?:total\s+plastic|plastic\s+usage)[^0-9]{0,15}[:\-]?\s*(\d{1,3}(?:[ ,]?\d{3})*(?:\.\d+)?)"
    },
    "recycled_plastic_share": {
        "keywords": ["Recycled plastic", "% recycled", "recycling rate"],
        "regex": r"(?:recycled[^0-9%]{0,10})[:\-]?\s*(\d{1,3}(?:\.\d+)?)\s?%"
    },
    "plastic_reduction_percent": {
        "keywords": ["Plastic reduction", "reduction in plastic", "plastic usage reduced"],
        "regex": r"(?:plastic[^%0-9]{0,20})[:\-]?\s*(-?\d{1,3}(?:\.\d+)?)\s?%"
    }
}

# -----------------------------------------------------------------------------
# Config
# -----------------------------------------------------------------------------
class Config:
    # MinIO
    MINIO_ENDPOINT  = os.getenv("MINIO_ENDPOINT",  "localhost:9000")
    MINIO_ACCESS_KEY= os.getenv("MINIO_ACCESS_KEY","ift_bigdata")
    MINIO_SECRET_KEY= os.getenv("MINIO_SECRET_KEY","minio_password")
    MINIO_BUCKET    = os.getenv("MINIO_BUCKET",   "report")

    # Postgres
    PG_HOST = os.getenv("PG_HOST", "localhost")
    PG_PORT = int(os.getenv("PG_PORT", 5439))          # 容器映射宿主 5439→5432
    PG_USER = os.getenv("PG_USER", "postgres")
    PG_PWD  = os.getenv("PG_PWD",  "postgres")
    PG_DB   = os.getenv("PG_DB",   "postgres")


    # Output
    JSON_PATH = "csr_output.json"

    # 👇 仅测试时填公司，留空处理全部
    TEST_COMPANIES: List[str] = []

# -----------------------------------------------------------------------------
# Helpers + Classes
# -----------------------------------------------------------------------------

def compute_hash(txt: str) -> str:
    return hashlib.md5(txt.encode()).hexdigest()

class IndicatorDB:
    def __init__(self):
        self.conn = psycopg2.connect(
            host=Config.PG_HOST, port=Config.PG_PORT, user=Config.PG_USER,
            password=Config.PG_PWD, database=Config.PG_DB,
        )
        self.cur = self.conn.cursor()
        self.cur.execute(
            """
            CREATE TABLE IF NOT EXISTS csr_indicators (
                id SERIAL PRIMARY KEY,
                company_id      VARCHAR(255),
                reporting_year  INT,
                data            JSONB,
                content_hash    VARCHAR(32),
                source_file     TEXT,
                created_at      TIMESTAMP DEFAULT NOW(),
                UNIQUE (company_id, reporting_year)
            );
            """
        )
        self.conn.commit()

    def upsert(self, rec: Dict[str, Any]):
        data_part = {k: v for k, v in rec.items() if k not in {
            "company_id", "reporting_year", "source_file_path", "__content_hash__"}}
        sql = (
            "INSERT INTO csr_indicators (company_id, reporting_year, data, content_hash, source_file) "
            "VALUES (%s,%s,%s,%s,%s) "
            "ON CONFLICT (company_id, reporting_year) DO UPDATE SET "
            "data = EXCLUDED.data, content_hash = EXCLUDED.content_hash, "
            "source_file = EXCLUDED.source_file, created_at = NOW();"
        )
        self.cur.execute(sql, (
            rec["company_id"], rec["reporting_year"], Json(data_part),
            rec["__content_hash__"], rec["source_file_path"],
        ))
        self.conn.commit()

    def fetch_pdf_records(self, companies: List[str]) -> List[tuple[str, int, str]]:
        base_q = "SELECT company, year, filename FROM pdf_records WHERE filename <> ''"
        if companies:
            placeholders = ",".join(["%s"] * len(companies))
            q = f"{base_q} AND company IN ({placeholders}) ORDER BY company, year;"
            self.cur.execute(q, tuple(companies))
        else:
            q = f"{base_q} ORDER BY company, year;"
            self.cur.execute(q)
        return self.cur.fetchall()

    def close(self):
        self.cur.close()
        self.conn.close()

class MinioReader:
    def __init__(self):
        self.cli = Minio(
            Config.MINIO_ENDPOINT,
            access_key=Config.MINIO_ACCESS_KEY,
            secret_key=Config.MINIO_SECRET_KEY,
            secure=False,
        )
    def get_bytes(self, obj_name: str) -> bytes | None:
        try:
            resp = self.cli.get_object(Config.MINIO_BUCKET, obj_name)
            try:
                return resp.read()
            finally:
                resp.close(); resp.release_conn()
        except S3Error:
            return None 

# -----------------------------------------------------------------------------
# Extraction
# -----------------------------------------------------------------------------

def extract(text: str, company: str, year: int, src: str) -> Dict[str, Any]:
    out = {
        "company_id": company,
        "reporting_year": year,
        "source_file_path": src,
        "__content_hash__": compute_hash(text),
    }
    sents = sent_tokenize(text)
    for field, cfg in field_patterns.items():
        pat = re.compile(cfg["regex"], re.IGNORECASE)
        max_val = None
        for sent in sents:
            for m in pat.finditer(sent):
                try:
                    val = float(m.group(1).replace(",","").replace(" ",""))
                    max_val = val if max_val is None or val > max_val else max_val
                except ValueError:
                    continue
        out[field] = max_val
    return out

# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------

def main():
    # 🔍 若命令行带公司参数则优先生效
    cli_companies = sys.argv[1:]
    companies = cli_companies or Config.TEST_COMPANIES

    db = IndicatorDB()
    minio_r = MinioReader()

    pdf_records = db.fetch_pdf_records(companies)
    if not pdf_records:
        print("⚠️  未找到匹配的 pdf_records！")
        return

    results: List[Dict[str, Any]] = []
    for comp, yr, fname in tqdm(pdf_records, desc="Extracting"):
        # 把 xxx.pdf 换成 xxx.txt
        txt_key = fname.rsplit(".", 1)[0] + ".txt"
        try:
            # 从 text bucket 读回文字
            text_bytes = minio_r.cli.get_object(Config.MINIO_BUCKET, txt_key).read()
            text = text_bytes.decode("utf-8")
        except S3Error:
            print(f"⚠️  {comp}-{yr} 找不到对应的文本文件 {txt_key}")
            continue

        # 直接把纯文本送进 extract
        rec = extract(text, comp, yr, f"minio://{Config.MINIO_BUCKET}/{txt_key}")
        db.upsert(rec)
        results.append(rec)

    # 写本地 JSON 方便人工检查
    with open(Config.JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"✅ 完成！共 {len(results)} 条，结果写入 {Config.JSON_PATH} + DB csr_indicators")
    db.close()

if __name__ == "__main__":
    main()