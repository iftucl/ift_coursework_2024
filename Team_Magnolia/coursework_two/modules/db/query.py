# modules/db/query.py
import json
from pymongo import MongoClient
from modules.extract.config_loader import MONGO_URI, MONGO_DB

def fetch_report(company_id: int, report_year: int = None) -> dict | None:
    """
    从 MongoDB 里根据 company_id（和可选的 report_year）查找一条报告文档。
    返回 Python dict，如果找不到返回 None。
    """
    client = MongoClient(MONGO_URI)
    db     = client[MONGO_DB]
    coll   = db["csr_reports_v2"]

    query = {"company_id": company_id}
    if report_year is not None:
        query["report_year"] = report_year

    return coll.find_one(query)
