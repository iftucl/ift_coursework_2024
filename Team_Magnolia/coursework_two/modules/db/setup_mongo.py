# coding: utf-8
"""
modules/db/setup_mongo.py

在 MongoDB 中创建一个新的 csr_reports_v2 集合（带 JSON Schema 验证器），
不删除已有集合 / Create a new 'csr_reports_v2' collection in MongoDB
with JSON Schema validation—do not delete existing collections.
"""

import os
from pymongo import MongoClient

# ─── 1) 读取连接信息 / Load connection URI ────────────────────────────────
MONGO_URI = os.getenv("MONGO_URI", "mongodb://mongo_db_cw:27017")
client    = MongoClient(MONGO_URI)

# ─── 2) 选择数据库 / Select database ────────────────────────────────────
db_name = "csr_extraction"          # 你自己的数据库名 / your database name
db      = client[db_name]

# ─── 3) 新集合名称 / New collection name ─────────────────────────────────
new_coll = "csr_reports_v2"         # 取一个新的名字，不覆盖旧的 / a new name, don't overwrite old

# ─── 4) 定义 JSON Schema 验证器 / Define JSON Schema validator ──────────
validator = {
    "$jsonSchema": {
        "bsonType": "object",
        "required": [
            "company_id",
            "report_year",
            "object_key",
            "ingestion_time",
            "version",
            "raw_data",
            "standardized_data"
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
        "additionalProperties": False  # 禁止多余字段 / disallow extra fields
    }
}

# ─── 5) 创建新集合（如果不存在） / Create new collection if not exists ──
if new_coll in db.list_collection_names():
    print(f"⚠️  Collection '{new_coll}' already exists in '{db_name}', skipping creation.")
else:
    db.create_collection(
        new_coll,
        validator=validator,
        validationLevel="strict",    # 严格模式 / strict validation
        validationAction="error"     # 验证失败时抛错 / reject invalid docs
    )
    print(f"✅  Created collection '{new_coll}' in database '{db_name}'.")
