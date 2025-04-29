import builtins
import types
from modules.data_storage import create_table

# 准备 Dummy 对象用于模拟数据库连接和游标行为
class DummyCursor:
    def __init__(self):
        self.executed_queries = []
    def execute(self, query):
        # 记录执行的 SQL 语句
        self.executed_queries.append(query)
    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc, tb):
        return False
class DummyConnection:
    def __init__(self):
        self.cursor_obj = DummyCursor()
        self.committed = False
        self.closed = False
    def cursor(self):
        return self.cursor_obj  # 返回 DummyCursor 上下文管理器
    def commit(self):
        self.committed = True
    def close(self):
        self.closed = True

def test_create_table_success(monkeypatch, capsys):
    """模拟正常创建表和插入数据的场景"""
    dummy_conn = DummyConnection()
    # monkeypatch psycopg2.connect 返回 dummy_conn
    monkeypatch.setattr(create_table.psycopg2, "connect", lambda **kwargs: dummy_conn)
    # monkeypatch execute_values 为空操作，避免实际插入
    monkeypatch.setattr(create_table, "execute_values", lambda cursor, sql, data: None)
    # 调用待测函数
    create_table.create_table_and_insert_data()
    # 捕获打印输出并验证成功消息
    captured = capsys.readouterr().out
    assert "created successfully" in captured  # 确认成功创建表的提示输出
    # 验证提交和关闭被调用
    assert dummy_conn.committed is True
    assert dummy_conn.closed is True

def test_create_table_insert_failure(monkeypatch, capsys):
    """模拟插入数据阶段发生异常的场景"""
    dummy_conn = DummyConnection()
    # 第一次 psycopg2.connect 成功，返回 dummy_conn
    monkeypatch.setattr(create_table.psycopg2, "connect", lambda **kwargs: dummy_conn)
    # monkeypatch execute_values 在插入时抛出异常，触发第二个 except
    def raise_error(cursor, sql, data):
        raise Exception("Insert failed")
    monkeypatch.setattr(create_table, "execute_values", raise_error)
    # 调用函数，插入阶段应触发异常处理
    create_table.create_table_and_insert_data()
    captured = capsys.readouterr().out
    # 检查是否打印了插入失败的错误消息
    assert "Error occurred" in captured and "Insert failed" in captured
    # 无论插入失败，最终都应关闭连接
    assert dummy_conn.closed is True

def test_create_table_connection_failure(monkeypatch, capsys):
    """模拟数据库连接失败的场景"""
    # monkeypatch psycopg2.connect 抛出异常，触发第一个 except 分支
    monkeypatch.setattr(create_table.psycopg2, "connect", lambda **kwargs: (_ for _ in ()).throw(Exception("Conn error")))
    # 调用函数，预期捕获连接异常
    create_table.create_table_and_insert_data()
    captured = capsys.readouterr().out
    assert "Error occurred" in captured and "Conn error" in captured
    # 尽管连接失败，本函数第二部分仍会尝试执行（代码需避免这种情况）。
    # 在这种情况下，dummy_conn 未创建，函数应安全退出（实际代码可能出现 NameError）。

