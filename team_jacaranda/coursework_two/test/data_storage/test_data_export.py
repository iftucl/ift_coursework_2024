import types
import pandas as pd
from modules.data_storage import data_export

def test_export_table_query_with_order(monkeypatch):
    """测试包含默认排序列时查询字符串是否正确附加 ORDER BY"""
    captured_query = {}
    # 模拟 pandas.read_sql_query 捕获传入的 SQL 查询
    def fake_read_sql(query, conn):
        captured_query["sql"] = query
        # 返回一个空的 DataFrame 对象
        return pd.DataFrame()
    monkeypatch.setattr(data_export, "pd", types.SimpleNamespace(read_sql_query=fake_read_sql, DataFrame=pd.DataFrame))
    # 模拟 DataFrame.to_csv 方法，记录输出路径
    output_path = "dummy_path.csv"
    called = {"to_csv": False, "path": None}
    def fake_to_csv(self, path, index=False, encoding=None):
        called["to_csv"] = True
        called["path"] = path
    # 替换 DataFrame.to_csv，全局影响所有 DataFrame 实例
    monkeypatch.setattr(pd.DataFrame, "to_csv", fake_to_csv, raising=False)
    # 使用在 default_order_columns 中的表调用
    table_name = "csr_reporting.company_reports"
    data_export.export_table_to_csv(table_name, output_path, conn="DummyConnection")
    # 验证查询包含 ORDER BY 对应的 id 列
    assert "ORDER BY id" in captured_query["sql"]
    # 验证 to_csv 被调用且路径正确
    assert called["to_csv"] is True and called["path"] == output_path

def test_export_table_query_without_order(monkeypatch):
    """测试无默认排序列时查询字符串不包含 ORDER BY"""
    captured_query = {}
    monkeypatch.setattr(data_export, "pd", types.SimpleNamespace(
        read_sql_query=lambda q, conn: (captured_query.update({"sql": q}) or pd.DataFrame()),
        DataFrame=pd.DataFrame))
    # 同样替换 DataFrame.to_csv
    monkeypatch.setattr(pd.DataFrame, "to_csv", lambda self, path, **kwargs: None, raising=False)
    # 调用一个不在 default_order_columns 字典中的表
    table_name = "some_schema.unknown_table"
    data_export.export_table_to_csv(table_name, "out.csv", conn="DummyConn")
    # 验证查询语句没有 ORDER BY 子句
    assert "ORDER BY" not in captured_query["sql"]

def test_main_exports_all_tables(monkeypatch):
    """测试 main() 函数按顺序导出所有表并关闭连接"""
    # 模拟 psycopg2.connect 返回带 close() 方法的 DummyConn
    closed_flag = {"closed": False}
    class DummyConn:
        def close(self):
            closed_flag["closed"] = True
    monkeypatch.setattr(data_export.psycopg2, "connect", lambda **kwargs: DummyConn())
    # 模拟 export_table_to_csv 记录调用的表名
    exported_tables = []
    monkeypatch.setattr(data_export, "export_table_to_csv",
                        lambda table, path, conn: exported_tables.append(table))
    # 执行 main()
    data_export.main()
    # modules 列表中应有的三个表均被导出调用
    expected_tables = ["csr_reporting.company_reports", "csr_reporting.csr_indicators", "csr_reporting.csr_data"]
    assert exported_tables == expected_tables
    # 验证连接关闭
    assert closed_flag["closed"] is True
