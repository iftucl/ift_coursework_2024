# coding: utf-8
"""
modules/db/mongo_client.py
────────────────────────────────────────────────────────────
MongoDB 轻量级客户端封装
Initialise a global MongoClient and expose `db` handle.
"""

from __future__ import annotations
import os
from pymongo import MongoClient
from modules.extract.config_loader import _cfg  # 直接拿 conf.yaml 里的整块配置

# 1) 先尝试 conf.yaml，再尝试环境变量
mongo_uri = (
    _cfg.get("database", {}).get("mongo_uri")
    or os.getenv("MONGO_URI", "mongodb://localhost:27019")
)
mongo_db_name = (
    _cfg.get("database", {}).get("mongo_db")
    or os.getenv("MONGO_DB", "csr_extraction")
)

client: MongoClient = MongoClient(mongo_uri)
db = client[mongo_db_name]

# 可选：简单连通性测试
try:
    client.admin.command("ping")
    print(f"✅  Mongo connected → {mongo_uri} / {mongo_db_name}")
except Exception as exc:
    print(f"⚠️  Mongo connection failed: {exc}")
