# modules/company_lookup.py

from typing import Optional
import re
from pymongo import MongoClient, ReturnDocument
from bson.objectid import ObjectId

from modules.extract.config_loader import MONGO_URI, MONGO_DB

def _normalize_name(name: str) -> str:
    """
    将公司名称规范化：去首尾空白、小写化、剔除标点、合并多余空格
    """
    if not name:
        return ""
    # 去首尾、转小写
    norm = name.strip().lower()
    # 删除所有非字母数字和空白字符（剔除标点）
    norm = re.sub(r"[^\w\s]", "", norm)
    # 合并多个空格
    norm = re.sub(r"\s+", " ", norm)
    return norm

def get_company_id(name: str) -> Optional[ObjectId]:
    """
    根据规范化后的名称在 dim_companies 中查找或新建一条记录，
    返回其 _id；若传入 name 为空或全是空白，则返回 None 并跳过。
    """
    norm = _normalize_name(name or "")
    if not norm:
        # 名称为空或全是空白，跳过
        return None

    # 直接用 MongoClient 连接
    client = MongoClient(MONGO_URI)
    db = client[MONGO_DB]
    coll = db["dim_companies"]

    try:
        # 原子 upsert：若已有 norm_name，则直接返回；否则插入 name 与 norm_name
        doc = coll.find_one_and_update(
            {"norm_name": norm},
            {"$setOnInsert": {"name": name.strip(), "norm_name": norm}},
            upsert=True,
            return_document=ReturnDocument.AFTER
        )
    except Exception:
        # 并发冲突时，回退到普通查找
        doc = coll.find_one({"norm_name": norm})
        if doc is None:
            # 如果仍然找不到，就让异常向上抛出，方便排查
            raise

    return doc.get("_id")
