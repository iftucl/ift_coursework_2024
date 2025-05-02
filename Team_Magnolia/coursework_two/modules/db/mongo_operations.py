# coding: utf-8
"""
modules/db/mongo_operations.py

封装将 CSR Data Catalogue 等文档保存到 MongoDB 的操作
Wraps operations to save CSR Data Catalogue and other documents into MongoDB
"""

from datetime import datetime
from pymongo.errors import PyMongoError
from .mongo_client import db       # 从 mongo_client 导入已初始化的 db 对象
from modules.extract.catalogue_loader import load_catalogue

def save_catalogue_to_mongo(collection_name: str = "csr_catalogue") -> bool:
    """
    Save the CSR Data Catalogue into MongoDB
    将 CSR 数据目录保存到 MongoDB 中的指定集合
    :param collection_name: MongoDB 中的集合名称 / the target collection name
    :return: True on success, False on failure
    """
    try:
        # 1) 加载 CSV -> DataFrame -> dict 列表
        df = load_catalogue()  
        docs = df.to_dict(orient="records")

        # 2) 获取集合引用
        coll = db[collection_name]

        # 3) （可选）先清空旧数据，再插入
        coll.delete_many({})

        # 4) 批量插入
        result = coll.insert_many(docs)
        count = len(result.inserted_ids)

        print(f"✅  Saved {count} catalogue entries into '{collection_name}' collection.")
        return True

    except FileNotFoundError as fe:
        print(f"❌  Catalogue file not found: {fe}")
        return False
    except PyMongoError as me:
        print(f"❌  MongoDB error: {me}")
        return False
    except Exception as e:
        print(f"❌  Unexpected error: {e}")
        return False
