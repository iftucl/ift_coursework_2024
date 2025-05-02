 # modules/db/setup_lineage.py
from pymongo import MongoClient

# 连接与数据库名要与 conf.yaml 中一致
client = MongoClient("mongodb://localhost:27019")
db = client["csr_extraction"]

# JSON Schema 验证器（可选）
validator = {
    "$jsonSchema": {
        "bsonType": "object",
        "required": ["_run_id", "timestamp", "input", "output_files"],
        "properties": {
            "_run_id":        {"bsonType": "string"},
            "timestamp":      {"bsonType": "string"},
            "input":          {"bsonType": "object"},
            "output_files":   {"bsonType": "object"},
        }
    }
}

# 如果集合已存在则跳过
if "csr_lineage" not in db.list_collection_names():
    db.create_collection("csr_lineage", validator=validator)
    print("✅  已创建集合 csr_lineage")
else:
    print("ℹ️  集合 csr_lineage 已存在，跳过创建")
