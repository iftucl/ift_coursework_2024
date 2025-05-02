import pytest
from modules.db import pg_client

class DummyCursor:
    def __init__(self):
        self.queries = []
    def execute(self, sql, params=None):
        self.queries.append((sql, params))
    def fetchone(self):
        return [42]  # 假定返回 company_id / indicator_id = 42
    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc, tb):
        pass

class DummyConn:
    def __init__(self):
        self.autocommit = False
        self.cur = DummyCursor()
    def cursor(self):
        return self.cur
    def close(self):
        pass

@pytest.fixture(autouse=True)
def fake_psycopg2_connect(monkeypatch):
    # 替换 psycopg2.connect → 返回 DummyConn
    import psycopg2
    monkeypatch.setattr(psycopg2, "connect", lambda dsn: DummyConn())

def test_upsert_company_and_indicator():
    cid = pg_client._upsert_company("norm","Display")
    assert cid == 42
    # cursor.queries[0] 是 INSERT SQL
    insert_sql, params = pg_client._get_default_cursor().queries[0]
    assert "INSERT INTO" in insert_sql

    iid = pg_client._upsert_indicator("slug","Name","Area")
    assert iid == 42
    # 同理检查 indicator upsert
