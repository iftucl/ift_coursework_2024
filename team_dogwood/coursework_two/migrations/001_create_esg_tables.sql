-- emissions  (Scope 1 / 2 / 3)
CREATE TABLE IF NOT EXISTS emissions (
    indicator_id   TEXT PRIMARY KEY,
    indicator_name TEXT,
    category       TEXT,
    company        TEXT,
    report_year    INT,
    figure         DOUBLE PRECISION,
    unit           TEXT,
    data_type      TEXT
);

-- energy  (energy + water)
CREATE TABLE IF NOT EXISTS energy (
    indicator_id   TEXT PRIMARY KEY,
    indicator_name TEXT,
    category       TEXT,
    company        TEXT,
    report_year    INT,
    figure         DOUBLE PRECISION,
    unit           TEXT,
    data_type      TEXT
);

-- waste  (waste & packaging)
CREATE TABLE IF NOT EXISTS waste (
    indicator_id   TEXT PRIMARY KEY,
    indicator_name TEXT,
    category       TEXT,
    company        TEXT,
    report_year    INT,
    figure         DOUBLE PRECISION,
    unit           TEXT,
    data_type      TEXT
);
