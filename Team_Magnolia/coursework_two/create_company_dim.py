from pymongo import MongoClient, ReturnDocument, UpdateOne
import re, unicodedata
import pymongo 

MONGO_URI = "mongodb://localhost:27019"
DB_NAME   = "csr_db"
SRC_COL   = "csr_reports"
DIM_COL   = "companies"

cli = MongoClient(MONGO_URI)
src   = cli[DB_NAME][SRC_COL]
dim   = cli[DB_NAME][DIM_COL]

# ── 1) canonicalize 函数：去掉符号、大小写、空白 ─────────────
def canon(txt: str) -> str:
    txt = unicodedata.normalize("NFKD", txt or "")
    txt = re.sub(r"[^\w\s]", "", txt).lower().strip()
    return txt

# ensure 索引
dim.create_index("name_norm", unique=True, sparse=True)

# ── 2) 主循环：扫描 csr_reports ──────────────────────────────
bulk_reports = []
for r in src.find({}, {"_id": 1, "company_name": 1}):
    name = r.get("company_name")
    norm = canon(name)
    if not norm:
        continue

    # (a) 在 companies 里 upsert
    doc = dim.find_one_and_update(
        {"name_norm": norm},
        {"$setOnInsert": {"name_en": name, "name_norm": norm}},
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )
    cid = doc["_id"]  # 直接用 ObjectId 当公司 id，也可另加递增字段

    # (b) 准备把 company_id 写回 csr_reports
    bulk_reports.append(
        pymongo.UpdateOne({"_id": r["_id"]}, {"$set": {"company_id": cid}})
    )

# ── 3) 批量回写 ───────────────────────────────────────────────
if bulk_reports:
    res = src.bulk_write(bulk_reports)
    print("reports updated:", res.modified_count)

print("companies total:", dim.count_documents({}))
