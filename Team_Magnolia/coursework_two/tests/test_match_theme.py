# tests/test_match_theme.py
import re
import pytest
from modules.extract.extractor import _match_theme

@pytest.fixture
def theme_cfg():
    return {
        "unit_re": re.compile(r"\$\d+"),
        "keyword_re": [re.compile(r"Revenue"), re.compile(r"Profit")],
        "require_multiple_year_occurrences": False,
        "min_keyword_hits": 1,
    }

def test_match_theme_positive(theme_cfg):
    # 包含 "$123" 单位，并且包含 "Revenue"
    text = "In 2023, Revenue grew to $123 million."
    assert _match_theme(text, theme_cfg)

def test_match_theme_negative_no_unit(theme_cfg):
    text = "Revenue grew but no dollar sign"
    assert not _match_theme(text, theme_cfg)

def test_match_theme_negative_no_keyword(theme_cfg):
    text = "In 2023 we saw $123."
    assert not _match_theme(text, theme_cfg)
