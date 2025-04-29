import pytest
import re
from modules.data_storage import llm_standardize
import json

class DummyCursor:
    def __init__(self):
        self.executed = False
        self.last_query = None
        self.last_params = None

    def execute(self, query, params=None):
        self.executed = True
        self.last_query = query
        self.last_params = params

    def close(self):
        pass

class DummyConnection:
    def __init__(self):
        self.cursor_obj = DummyCursor()
        self.committed = False
        self.rolled_back = False
        self.closed = False

    def cursor(self):
        return self.cursor_obj

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True

    def close(self):
        self.closed = True


# 重用 DummyConnection 和 DummyCursor

def test_safe_json_parse_cleanup_and_errors():
    # 带有```json 包裹的字符串应正确解析
    raw = "```json\n{\"convertibility\": true, \"value_standardized\": \"100\"}\n```"
    parsed = llm_standardize.safe_json_parse(raw)
    assert parsed == {"convertibility": True, "value_standardized": "100"}
    # 纯空内容（或只有格式包裹空）应抛出 ValueError
    with pytest.raises(ValueError):
        llm_standardize.safe_json_parse("```\n```")
    # 无效 JSON 内容应抛出 JSONDecodeError
    with pytest.raises(json.JSONDecodeError):
        llm_standardize.safe_json_parse("not a json")

def test_build_conversion_prompt_content():
    prompt = llm_standardize.build_conversion_prompt(
        "Energy Intensity", "Measures energy usage", "50", "kWh", "kWh"
    )
    # 检查生成的提示包含关键内容
    assert "indicator is \"Energy Intensity\"" in prompt
    assert "raw value as: 50" in prompt and "original unit: kWh" in prompt
    assert "target unit \"kWh\"" in prompt
    assert "\"convertibility\": true" in prompt  # 输出格式示例部分

def test_update_standardized_execution(monkeypatch):
    dummy_conn = DummyConnection()
    # 执行 update_standardized
    llm_standardize.update_standardized(dummy_conn, data_id=5, value_standardized="123", unit_standardized="kg", unit_conversion_note="note")
    # 检查 SQL 执行及参数
    cur = dummy_conn.cursor_obj
    assert cur.executed is True
    assert "UPDATE csr_reporting.CSR_Data" in cur.last_query
    # 确认 commit 调用
    assert dummy_conn.committed is True

def test_process_row_unit_match(monkeypatch):
    """测试 process_row 单位相同直接返回的分支"""
    dummy_conn = DummyConnection()
    # monkeypatch update_standardized 捕获参数
    updated = []
    monkeypatch.setattr(llm_standardize, "update_standardized", lambda conn, did, val, unit, note=None: updated.append((did, val, unit, note)))
    row = (10, "Water Usage", "100", "L", " l ", "desc",)  # unit_raw "L" vs target_unit " l " (仅大小写和空格差异)
    result = llm_standardize.process_row(dummy_conn, row)
    # 应直接返回 data_id，update_standardized 用原值
    assert result == 10
    assert updated and updated[0][:3] == (10, "100", " l ")  # 单位匹配时记录note指示无需转换
    assert "no conversion needed" in updated[0][3]
    # 确认未调用 LLM，无 rollback
    assert dummy_conn.rolled_back is False

def test_process_row_convertible_false(monkeypatch):
    """测试 LLM 返回不可转换 (convertibility=False) 的情况"""
    dummy_conn = DummyConnection()
    # 模拟 call_llm 返回 convertibility false 的 JSON
    monkeypatch.setattr(llm_standardize, "call_llm", lambda prompt: '{"convertibility": false, "note": "unsupported"}')
    updated = []
    monkeypatch.setattr(llm_standardize, "update_standardized", lambda conn, did, val, unit, note=None: updated.append((did, val, unit, note)))
    # 构造需要转换的行（单位不同）
    row = (11, "Metric X", "5", "tons", "kg", "desc")
    result = llm_standardize.process_row(dummy_conn, row)
    # 返回 None 表示未转换，update_standardized 应收到 val=None, unit=None, note 来记录原因
    assert result is None
    assert updated and updated[0][0] == 11 and updated[0][1] is None and updated[0][2] is None
    assert updated[0][3] == "unsupported"
    # 打印警告包含 reason，且无异常抛出
    assert dummy_conn.rolled_back is False

def test_process_row_invalid_result_value(monkeypatch, capsys):
    """测试 LLM 返回可转换但结果不是数字的情况"""
    dummy_conn = DummyConnection()
    # 模拟 call_llm 返回 convertibility true 但 value_standardized 非数字
    monkeypatch.setattr(llm_standardize, "call_llm", lambda prompt: '{"convertibility": true, "value_standardized": "N/A", "note": "not numeric"}')
    # monkeypatch safe_json_parse 使用真实函数解析
    # 不 monkeypatch update_standardized，使其走 DummyConnection 正常执行
    row = (12, "Metric Y", "7", "%", "%", "desc")  # 单位不同才会调用 LLM，这里给不同单位
    result = llm_standardize.process_row(dummy_conn, row)
    # 因 value_standardized 非法，函数应捕获异常，rollback，并返回 None
    assert result is None
    assert dummy_conn.rolled_back is True
    # 捕获输出，检查包含失败信息和原始 LLM 响应
    output = capsys.readouterr().out
    assert f"Data ID {row[0]} standardization failed" in output
    assert "N/A" in output  # 原始LLM响应或错误原因输出

def test_process_row_success(monkeypatch):
    """测试 LLM 转换成功的完整流程"""
    dummy_conn = DummyConnection()
    # 模拟 call_llm 返回有效的 JSON
    monkeypatch.setattr(llm_standardize, "call_llm", lambda prompt: '{"convertibility": true, "value_standardized": "42.0", "note": "OK"}')
    updated = []
    monkeypatch.setattr(llm_standardize, "update_standardized", lambda conn, did, val, unit, note=None: updated.append((did, val, unit, note)))
    row = (13, "Metric Z", "100", "kg", "tons", "desc")
    result = llm_standardize.process_row(dummy_conn, row)
    # 应返回 data_id，且 update_standardized 用转换后的值和目标单位
    assert result == 13
    assert updated and updated[0][0] == 13 and updated[0][1] == "42.0" and updated[0][2] == "tons"
    # 确认无 rollback，commit 已在 update_standardized 内调用
    assert dummy_conn.rolled_back is False
    assert dummy_conn.committed is True

def test_main_standardization_pipeline(monkeypatch, capsys):
    """测试 main() 函数整体流程，包括批量处理和文件输出逻辑"""
    dummy_conn = DummyConnection()
    monkeypatch.setattr(llm_standardize, "get_connection", lambda: dummy_conn)
    # 模拟待标准化的两条记录
    rows = [
        (21, "IndA", "10", "m3", "m3", "descA"),   # 单位相同，将直接返回
        (22, "IndB", "5", "kg", "g", "descB")      # 单位不同，将调用 LLM 转换
    ]
    monkeypatch.setattr(llm_standardize, "fetch_rows_to_standardize", lambda conn: rows)
    # monkeypatch process_row：第一条返回data_id, 第二条返回None模拟转换失败
    def fake_process_row(conn, row):
        return row[0] if row[0] == 21 else None
    monkeypatch.setattr(llm_standardize, "process_row", fake_process_row)
    # 替换 ThreadPoolExecutor 和 as_completed 使同步执行
    class DummyFuture:
        def __init__(self, result): self._result = result
        def result(self): return self._result
    class DummyExecutor:
        def __enter__(self): return self
        def __exit__(self, exc_type, exc, tb): return False
        def submit(self, func, *args):
            return DummyFuture(func(*args))
    monkeypatch.setattr(llm_standardize, "ThreadPoolExecutor", lambda max_workers=None: DummyExecutor())
    monkeypatch.setattr(llm_standardize, "as_completed", lambda futures, **kwargs: futures)
    # 替换 tqdm，使其不影响输出
    monkeypatch.setattr(llm_standardize, "tqdm", lambda iterable=None, **kwargs: iterable if iterable is not None else types.SimpleNamespace(close=lambda: None, update=lambda x: None))
    # 执行 main()
    llm_standardize.main()
    out = capsys.readouterr().out
    # 应打印需要标准化的记录数量
    assert "2 records need to be standardized" in out
    # 最终连接应关闭
    assert dummy_conn.closed is True

