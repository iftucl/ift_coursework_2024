-- modules/Schema.sql
-- ===============================================================
--  Coursework-2 ESG 指标的关系型架构
--  • 一家公司  ➜ 多个报告
--  • 一个指标  ➜ 多个年度观测值或承诺
-- ===============================================================

CREATE SCHEMA IF NOT EXISTS csr_reporting;

-- ────────────────────────────────────────────────────────────
-- 维度表
-- ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS csr_reporting.company_dim (
    company_id     SERIAL PRIMARY KEY,
    norm_name      TEXT NOT NULL UNIQUE,              -- 规范化名称，例如 “apple inc”
    display_name   TEXT                               -- 显示名称，例如 “Apple Inc.”
);

CREATE TABLE IF NOT EXISTS csr_reporting.indicator_dim (
    indicator_id   SERIAL PRIMARY KEY,
    slug           TEXT NOT NULL UNIQUE,              -- 指标标识符，例如 “scope1_emissions”
    indicator_name TEXT NOT NULL,                     -- 指标完整名称
    thematic_area  TEXT NOT NULL                      -- 主题领域，例如 “Environment”
);

-- ────────────────────────────────────────────────────────────
-- 事实表
-- ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS csr_reporting.csr_indicators (
    pk                BIGSERIAL PRIMARY KEY,
    company_id        INT  REFERENCES csr_reporting.company_dim   (company_id),
    indicator_id      INT  REFERENCES csr_reporting.indicator_dim (indicator_id),
    report_year       INT,            -- 报告年份
    indicator_year    INT,            -- 指标年份
    value_numeric     DOUBLE PRECISION,
    value_text        TEXT,
    unit              TEXT,
    page_number       INT[],          -- 页码数组
    source            TEXT,
    ingested_at       TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS csr_reporting.csr_commitments (
    pk                BIGSERIAL PRIMARY KEY,
    company_id        INT  REFERENCES csr_reporting.company_dim   (company_id),
    indicator_id      INT  REFERENCES csr_reporting.indicator_dim (indicator_id),
    goal_text         TEXT,           -- 承诺/目标文本
    progress_text     TEXT,
    baseline_year     INT,
    target_year       INT,
    target_value      DOUBLE PRECISION,
    target_unit       TEXT,
    page_number       INT[],
    source            TEXT,
    ingested_at       TIMESTAMPTZ DEFAULT now()
);

-- 有助于查询的索引
CREATE INDEX IF NOT EXISTS idx_csr_ind_company_year
    ON csr_reporting.csr_indicators    (company_id, indicator_year);

CREATE INDEX IF NOT EXISTS idx_csr_com_company_target
    ON csr_reporting.csr_commitments   (company_id, target_year);
