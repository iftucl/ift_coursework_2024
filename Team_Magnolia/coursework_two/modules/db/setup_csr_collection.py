# coding: utf-8
"""
modules/db/setup_csr_collection.py

在 MongoDB 中为 csr_extraction 数据库创建 csr_reports_v2 集合，
并附加 JSON Schema 验证器（不删除已有集合）
"""
import os
from pymongo import MongoClient

# ─── 1) 连接信息 / Connect to MongoDB ──────────────────────────
# 中英：从环境变量读取 URI，或 fallback 本地映射  localhost:27019
# EN: Load URI from env or default to localhost:27019
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27019")
client    = MongoClient(MONGO_URI)

# ─── 2) 选择数据库 / Select database ────────────────────────────
db = client["csr_extraction"]  # 中英：目标数据库名 / target database

# ─── 3) 新集合名 / New collection name ─────────────────────────
coll_name = "csr_reports_v2"

# ─── 4) JSON Schema 验证规则 / JSON Schema validator ─────────────
validator = {
    "$jsonSchema": {
        "bsonType": "object",
        "required": [
            "company_id", "report_year", "object_key",
            "ingestion_time", "version", "raw_data", "standardized_data"
        ],
        "properties": {
            "company_id":        {"bsonType": "string"},
            "report_year":       {"bsonType": "int"},
            "object_key":        {"bsonType": "string"},
            "ingestion_time":    {"bsonType": "date"},
            "version":           {"bsonType": "int"},
            "raw_data":          {"bsonType": "object"},
            "standardized_data": {"bsonType": "object"}
        },
        "additionalProperties": False
    }
}

# ─── 5) 创建集合（若不存在）/ Create if missing ─────────────────
if coll_name in db.list_collection_names():
    print(f"⚠️  Collection '{coll_name}' already exists, skipping.")
else:
    db.create_collection(
        coll_name,
        validator=validator,
        validationLevel="strict",
        validationAction="error"
    )
    print(f"✅  Created collection '{coll_name}' with schema validation.")
