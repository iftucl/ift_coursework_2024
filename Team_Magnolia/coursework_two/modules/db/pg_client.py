# modules/db/pg_client.py
# -------------------------------------------------------------
#  一个进程中重用单个（非异步安全）连接的小型包装
# -------------------------------------------------------------
import os
import psycopg2
from psycopg2.extras import execute_values

from modules.extract.config_loader import POSTGRES_URI, POSTGRES_SCHEMA

# 全局连接（重用）——对 CLI 用途来说足够简单
_conn = psycopg2.connect(POSTGRES_URI)
_conn.autocommit = True


def get_cursor():
    """
    上下文管理器，自动关闭游标。
    用法示例：
        with get_cursor() as cur:
            cur.execute("SELECT 1")
    """
    return _conn.cursor()


# ──────────────────────────────────────────────────────────────
# Upsert 辅助函数
# ──────────────────────────────────────────────────────────────
def _upsert_company(name_norm: str, name_display: str | None) -> int:
    """
    确保 company_dim 中存在该公司行，并返回 company_id。
    使用 ON CONFLICT (norm_name) 避免重复。
    """
    sql = f"""
    INSERT INTO {POSTGRES_SCHEMA}.company_dim (norm_name, display_name)
    VALUES (%s, %s)
    ON CONFLICT (norm_name) DO UPDATE
        SET display_name = EXCLUDED.display_name
    RETURNING company_id;
    """
    with get_cursor() as cur:
        cur.execute(sql, (name_norm, name_display))
        return cur.fetchone()[0]


def _upsert_indicator(slug: str, name: str, area: str) -> int:
    """
    确保 indicator_dim 中存在该指标行，并返回 indicator_id。
    """
    sql = f"""
    INSERT INTO {POSTGRES_SCHEMA}.indicator_dim (slug, indicator_name, thematic_area)
    VALUES (%s, %s, %s)
    ON CONFLICT (slug) DO UPDATE
        SET indicator_name = EXCLUDED.indicator_name,
            thematic_area  = EXCLUDED.thematic_area
    RETURNING indicator_id;
    """
    with get_cursor() as cur:
        cur.execute(sql, (slug, name, area))
        return cur.fetchone()[0]


def batch_insert_metrics(rows: list[dict]):
    """一次性插入多条度量型记录。"""
    if not rows:
        return
    tmpl = f"""
    INSERT INTO {POSTGRES_SCHEMA}.csr_indicators
      (company_id, indicator_id, report_year, indicator_year,
       value_numeric, value_text, unit, page_number, source)
    VALUES %s
    ON CONFLICT DO NOTHING;
    """
    values = [
        (r["company_id"], r["indicator_id"], r.get("report_year"),
         r.get("indicator_year"), r.get("value_numeric"),
         r.get("value_text"), r.get("unit"),
         r.get("page_number"), r.get("source"))
        for r in rows
    ]
    with get_cursor() as cur:
        execute_values(cur, tmpl, values, page_size=100)


def batch_insert_targets(rows: list[dict]):
    """一次性插入多条承诺/目标型记录。"""
    if not rows:
        return
    tmpl = f"""
    INSERT INTO {POSTGRES_SCHEMA}.csr_commitments
      (company_id, indicator_id, goal_text, progress_text,
       baseline_year, target_year, target_value, target_unit,
       page_number, source)
    VALUES %s
    ON CONFLICT DO NOTHING;
    """
    values = [
        (r["company_id"], r["indicator_id"], r.get("goal_text"),
         r.get("progress_text"), r.get("baseline_year"), r.get("target_year"),
         r.get("target_value"), r.get("target_unit"),
         r.get("page_number"), r.get("source"))
        for r in rows
    ]
    with get_cursor() as cur:
        execute_values(cur, tmpl, values, page_size=100)
