# tests/test_numeric_utils.py
import pytest
from modules.db.ingest import _safe_eval, _num_from_str

@pytest.mark.parametrize("expr,expected", [
    ("1+2", 3.0),
    ("10 / 4", 2.5),
    ("-5*3", -15.0),
    ("2^3", None),      # 不支持 ^
    ("not a num", None),
])
def test_safe_eval(expr, expected):
    assert _safe_eval(expr) == expected

@pytest.mark.parametrize("txt,expected", [
    ("≈ 1,234", 1234.0),
    ("123", 123.0),
    ("-7.5", -7.5),
    ("no numbers here", None),
])
def test_num_from_str(txt, expected):
    assert _num_from_str(txt) == expected
