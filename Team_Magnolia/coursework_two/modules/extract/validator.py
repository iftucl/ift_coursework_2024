# -*- coding: utf-8 -*-
"""
Validator for CSR records
────────────────────────────────────────────────────────────────────
Reads per-field rules from in-memory DATA_DICT (loaded by config_loader)
and applies them to a *single* flattened record (dict).  Raises
`ValueError` on the first rule that fails so the caller can decide
whether to skip the row or abort the pipeline.
"""

from __future__ import annotations

import re
import datetime
from typing import Dict, Any

from modules.extract.config_loader import DATA_DICT  # YAML/JSON → dict

# ─── quick anti-corruption check ─────────────────────────────────
if not isinstance(DATA_DICT, dict):
    raise TypeError(
        f"DATA_DICT must be <dict>, got {type(DATA_DICT)}. "
        "Check modules/config_loader.py – do not overwrite it with a Path."
    )

CURRENT_YEAR = datetime.date.today().year


# ────────────────────────────────────────────────────────────────
# helpers
# ────────────────────────────────────────────────────────────────
def _regex(pattern: str, value: str) -> bool:
    """Return True iff *value* matches regex *pattern* (full-match)."""
    return bool(re.fullmatch(pattern, str(value)))


def _check(rule: str, value: Any) -> bool:
    """
    Very small rule-engine – supports the patterns we defined in YAML.
    Extend here when you add new rule types.
    """
    # ① non-empty -------------------------------------------------
    if rule == "non-empty":
        return value not in (None, "", [], {})

    # ② numeric lower-bound --------------------------------------
    if rule.startswith(">="):
        thresh = float(rule.split(">=")[1].strip())
        try:
            return float(value) >= thresh
        except (TypeError, ValueError):
            return False

    # ③ regex match ----------------------------------------------
    if rule.startswith("matches regex"):
        pattern = rule.split("regex", 1)[1].strip()
        return _regex(pattern, str(value))

    # ④ value in whitelist ---------------------------------------
    if rule.startswith("in ["):
        # YAML 中写死的 list，安全可 eval
        allowed = eval(rule.split("in", 1)[1].strip())
        return value in allowed

    # ⑤ 年份区间 --------------------------------------------------
    if "value <= current_year" in rule:
        lower = int(rule.split("<=")[0].strip())
        try:
            v = int(value)
            return lower <= v <= CURRENT_YEAR
        except (TypeError, ValueError):
            return False

    # ⑥ baseline_year <= indicator_year 交叉验证占位
    if "<= indicator_year" in rule:
        return True  # 实际检查放到 cross-field 区

    # ⑦ 允许 null 的规则一律先放行
    if "null" in rule:
        return True

    # ⑧ 未识别的 rule 默认通过（可改为 False 强制显错）
    return True


# ────────────────────────────────────────────────────────────────
# public API
# ────────────────────────────────────────────────────────────────
def validate_record(rec: Dict[str, Any]) -> None:
    """
    Validate one flattened record.
    Raises `ValueError` 当校验失败。
    """
    # ---------- 单字段校验 ----------------------------------------------------
    for field, rules in DATA_DICT.items():
        rule = rules.get("validation")
        if rule is None:
            continue  # no rule → skip

        if not _check(rule, rec.get(field)):
            raise ValueError(
                f"Validation failed on field '{field}': "
                f"value={rec.get(field)!r}  rule=({rule})"
            )

    # ---------- 交叉字段校验 --------------------------------------------------
    # 1) values_numeric vs values_text 不能同时有值
    if rec.get("values_numeric") is not None and rec.get("values_text"):
        raise ValueError("Both values_numeric and values_text are set – choose one")

    # 2) baseline_year ≤ min(years)
    if rec.get("baseline_year") and rec.get("years"):
        try:
            baseline = int(rec["baseline_year"])
            yr = (
                min(rec["years"])
                if isinstance(rec["years"], list)
                else int(rec["years"])
            )
            if baseline > yr:
                raise ValueError("baseline_year > indicator year")
        except (TypeError, ValueError):
            raise ValueError("Invalid year format in 'years' or 'baseline_year'")

    # 3) indicator years ≤ target_year
    if rec.get("target_year") and rec.get("years"):
        try:
            target = int(rec["target_year"])
            yr = (
                max(rec["years"])
                if isinstance(rec["years"], list)
                else int(rec["years"])
            )
            if target < yr:
                raise ValueError("target_year < indicator year")
        except (TypeError, ValueError):
            raise ValueError("Invalid year format in 'years' or 'target_year'")
