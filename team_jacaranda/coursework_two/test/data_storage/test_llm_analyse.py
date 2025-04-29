import pytest
import json
import builtins
from modules.data_storage import llm_analyse

# 重用先前定义的 DummyConnection 和 DummyCursor 类
class DummyCursor:
    def __init__(self):
        self.executed = False
        self.last_query = None
        self.last_params = None
    def execute(self, query, params=None):
        self.executed = True
        self.last_query = query
        self.last_params = params
    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc, tb):
        return False
class DummyConnection:
    def __init__(self):
        self.committed = False
        self.rolled_back = False
        self.closed = False
        self.cursor_obj = DummyCursor()
    def cursor(self):
        return self.cursor_obj
    def commit(self):
        self.committed = True
    def rollback(self):
        self.rolled_back = True
    def close(self):
        self.closed = True

def test_build_prompt_target_vs_non_target():
    """测试 build_prompt 函数在目标类和非目标类情况下的输出"""
    sample_excerpt = [ {"page": 5, "text": "Sample paragraph content."} ]
    prompt_target = llm_analyse.build_prompt(
        "Carbon Neutrality Target", "Target description", True, sample_excerpt, 2025
    )
    prompt_nontarget = llm_analyse.build_prompt(
        "Carbon Intensity", "Indicator description", False, sample_excerpt, 2025
    )
    # 目标类提示应包含特定引导语句，例如关于 goals
    assert "goal-oriented" in prompt_target and "multiple sentences allowed" in prompt_target
    # 非目标类提示应包含提取数值的说明
    assert "numeric value" in prompt_nontarget and "\"unit\"" in prompt_nontarget

def test_is_valid_number():
    assert llm_analyse.is_valid_number("123.45") is True
    assert llm_analyse.is_valid_number("abc") is False
    # None 或空字符串等异常输入也应返回 False
    assert llm_analyse.is_valid_number("") is False
    assert llm_analyse.is_valid_number(None) is False

def test_update_result_executes_commit(monkeypatch):
    """测试 update_result 执行 UPDATE 语句并提交"""
    dummy_conn = DummyConnection()
    monkeypatch.setattr(llm_analyse, "client", None)  # 不涉及 client，这里可不需要
    # 使用 dummy_conn 调用 update_result
    llm_analyse.update_result(dummy_conn, data_id=1, value_raw="val", unit_raw="unit",
                              llm_response_raw="raw response", pdf_page="1,2")
    # 验证 execute 被调用且参数包含我们传入的值
    assert dummy_conn.cursor_obj.executed is True
    assert "UPDATE csr_reporting.CSR_Data" in dummy_conn.cursor_obj.last_query
    # 确认 commit 调用
    assert dummy_conn.committed is True

def test_process_row_target_json_and_nonjson(monkeypatch):
    """测试 is_target=True 情况下 JSON 可解析和不可解析输出"""
    dummy_conn = DummyConnection()
    # 模拟 call_llm：第一次返回可解析 JSON，第二次返回非JSON字符串
    outputs = [
        '{"value": "Goal achieved"}',  # valid JSON
        'Not a JSON text'             # invalid JSON
    ]
    call_count = {"count": 0}
    def fake_call_llm(prompt):
        result = outputs[call_count["count"]]
        call_count["count"] += 1
        return result
    monkeypatch.setattr(llm_analyse, "call_llm", fake_call_llm)
    # monkeypatch update_result 以记录传入的值而不实际访问数据库
    updated = []
    def fake_update(conn, data_id, value_raw, unit_raw, llm_resp, pages):
        updated.append((data_id, value_raw, unit_raw))
    monkeypatch.setattr(llm_analyse, "update_result", fake_update)
    # 准备示例输入行 (data_id, indicator_name, source_excerpt, indicator_id, report_year, description, is_target)
    row = (42, "Target Indicator", [{"page": 1, "text": "para"}], 1, 2025, "desc", True)
    # 调用 process_row 两次：第一次 JSON 正常解析，第二次 JSONDecodeError
    data_id_ret1 = llm_analyse.process_row(dummy_conn, row)
    data_id_ret2 = llm_analyse.process_row(dummy_conn, row)
    # 第一次应返回 data_id，value_raw 应来自解析后的 JSON
    assert data_id_ret1 == 42
    assert updated[0][0] == 42 and updated[0][1] == "Goal achieved" and updated[0][2] is None
    # 第二次应仍返回 data_id，即使 JSON 解析失败，value_raw 应为原始字符串，unit_raw 仍为 None
    assert data_id_ret2 == 42
    assert updated[1][0] == 42 and updated[1][1] == "Not a JSON text" and updated[1][2] is None
    # 确认未触发 rollback（因为目标类解析失败不抛异常）
    assert dummy_conn.rolled_back is False

def test_process_row_target_non_str_output(monkeypatch):
    """测试 is_target=True 且 LLM 输出非字符串类型的情况"""
    dummy_conn = DummyConnection()
    # 模拟 call_llm 返回 bytes 而不是 str
    monkeypatch.setattr(llm_analyse, "call_llm", lambda prompt: b" Byte response ")
    monkeypatch.setattr(llm_analyse, "update_result", lambda *args, **kwargs: None)
    row = (1, "Some Target", [{"page": 1, "text": "x"}], 1, 2022, "desc", True)
    result = llm_analyse.process_row(dummy_conn, row)
    # bytes.strip() 将去除空白，但仍是 bytes 类型; 函数应返回 data_id 而未出错
    assert result == 1
    # 确认未抛异常且未 rollback
    assert dummy_conn.rolled_back is False

def test_process_row_nontarget_invalid_number(monkeypatch):
    """测试 is_target=False 且值非数字触发 ValueError 的情况"""
    dummy_conn = DummyConnection()
    # 模拟 call_llm 返回 JSON，其中 value 非数字
    monkeypatch.setattr(llm_analyse, "call_llm", lambda prompt: '{"value": "N/A", "unit": "kg"}')
    # 不 monkeypatch update_result 因为不会执行到更新
    row = (100, "Indicator", [{"page": 1, "text": "y"}], 1, 2021, "desc", False)
    # 调用 process_row，应该抛出 ValueError 并 rollback
    with pytest.raises(ValueError):
        llm_analyse.process_row(dummy_conn, row)
    assert dummy_conn.rolled_back is True

def test_process_row_nontarget_json_error(monkeypatch):
    """测试 is_target=False 且 JSON 格式错误触发解析异常的情况"""
    dummy_conn = DummyConnection()
    monkeypatch.setattr(llm_analyse, "call_llm", lambda prompt: "invalid json")
    row = (101, "Indicator2", [{"page": 2, "text": "z"}], 2, 2020, "desc", False)
    with pytest.raises(json.JSONDecodeError):
        llm_analyse.process_row(dummy_conn, row)
    # 解析异常也应 rollback
    assert dummy_conn.rolled_back is True

def test_main_concurrent_processing(monkeypatch, capsys):
    """测试 main() 函数的多线程处理逻辑，包括成功和失败任务"""
    dummy_conn = DummyConnection()
    # monkeypatch 数据库连接和提取待处理行
    monkeypatch.setattr(llm_analyse, "get_connection", lambda: dummy_conn)
    # 模拟两条待处理记录
    rows = [
        (1, "Ind1", [], 1, 2020, "desc1", False),
        (2, "Ind2", [], 2, 2021, "desc2", False)
    ]
    monkeypatch.setattr(llm_analyse, "fetch_pending_rows", lambda conn: rows)
    # 模拟 process_row：data_id=1 返回正常，data_id=2 抛异常
    def fake_process_row(conn, row):
        if row[0] == 1:
            return row[0]  # 成功返回 data_id
        else:
            raise Exception("processing failed")
    monkeypatch.setattr(llm_analyse, "process_row", fake_process_row)
    # 替换 ThreadPoolExecutor 为 Dummy，使 submit 同步执行
    class DummyFuture:
        def __init__(self, result=None, exception=None):
            self._result = result
            self._exc = exception
        def result(self):
            if self._exc:
                raise self._exc
            return self._result
    class DummyExecutor:
        def __enter__(self): return self
        def __exit__(self, exc_type, exc, tb): return False
        def submit(self, func, *args):
            try:
                res = func(*args)
                return DummyFuture(result=res)
            except Exception as e:
                return DummyFuture(exception=e)
    monkeypatch.setattr(llm_analyse, "ThreadPoolExecutor", lambda max_workers=None: DummyExecutor())
    # 替换 as_completed 为直接返回 futures 列表
    monkeypatch.setattr(llm_analyse, "as_completed", lambda futures, **kwargs: futures)
    # 替换 tqdm 为直接使用可迭代对象（避免进度条干扰输出）
    monkeypatch.setattr(llm_analyse, "tqdm", lambda iterable, **kwargs: iterable)
    # 执行 main()
    llm_analyse.main()
    out = capsys.readouterr().out
    # 成功的任务应输出成功消息，失败的应输出失败消息
    assert "Successfully processed" in out
    assert "Processing failed" in out
    # 最终应关闭连接
    assert dummy_conn.closed is True
