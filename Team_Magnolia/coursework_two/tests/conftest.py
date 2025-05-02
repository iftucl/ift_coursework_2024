# tests/conftest.py

import os, sys

# ─── 确保 modules/ 在 sys.path 里 ────────────────────────────────
# __file__ 指向 tests/conftest.py，往上一层就是 coursework_two 目录，里面有 modules/
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import tempfile
import pytest
import mongomock
import psycopg2

from modules.db import pg_client  # 现在能正常 import 了

@pytest.fixture(autouse=True)
def env_vars(tmp_path, monkeypatch):
    """
    自动设置环境变量：
      - OUTPUT_DIR 指向 tmp 目录，
      - 用 mongomock 替换 MongoClient，
      - 尝试初始化 postgres schema，但失败也不报错。
    """
    monkeypatch.setenv("OUTPUT_DIR", str(tmp_path))
    monkeypatch.setenv("MONGO_URI", "mongodb://localhost:27017")
    # 测试用的 Postgres URI，优先 TEST_POSTGRES_URI
    test_pg_uri = os.getenv(
        "TEST_POSTGRES_URI",
        "postgresql://postgres:postgres@localhost:5432/fift"
    )
    monkeypatch.setenv("POSTGRES_URI", test_pg_uri)

    # 尝试重建 schema，不成功也无所谓
    try:
        conn = psycopg2.connect(test_pg_uri)
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute("DROP SCHEMA IF EXISTS csr_reporting CASCADE;")
            # 假设你的 Schema.sql 在 modules/db/Schema.sql
            cur.execute(open("modules/db/Schema.sql").read())
        conn.close()
    except Exception as e:
        print(f"[WARNING] skip PG schema setup: {e}")

    yield

@pytest.fixture
def mongo_client(monkeypatch):
    """
    全局把 pymongo.MongoClient 替换成 mongomock。
    """
    import pymongo
    monkeypatch.setattr(
        pymongo, "MongoClient",
        lambda *args, **kwargs: mongomock.MongoClient()
    )
    return mongomock.MongoClient()
