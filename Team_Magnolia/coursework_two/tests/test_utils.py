import pytest
from modules.db.ingest import _safe_eval, _num_from_str, _clean_numeric

def test_safe_eval_simple():
    # 简单算术
    assert _safe_eval("3+4*2") == 11.0
    # 近似比值计算
    result = _safe_eval("1770000/1832000*100")
    assert pytest.approx(result, rel=1e-3) == 96.62

def test_safe_eval_bad():
    # 非法表达式返回 None
    assert _safe_eval("foo + bar") is None

def test_num_from_str():
    # 去逗号、特殊符号后提取数字
    assert _num_from_str("≈ 1,234") == 1234.0
    # 破折号无数字返回 None
    assert _num_from_str("–") is None
    # 遇到“or null”提取第一个数字
    assert _num_from_str("10 or null") == 10.0

def test_clean_numeric_scalar_and_list():
    # 列表和标量都能处理
    rec = {"values_numeric": ["100", "200"], "target_value": "300"}
    _clean_numeric(rec, "values_numeric")
    _clean_numeric(rec, "target_value")
    assert rec["values_numeric"] == [100.0, 200.0]
    assert rec["target_value"] == 300.0
