import psycopg2
from jsonschema import validate, ValidationError

# =============================
#        CONFIGURATION
# =============================

def _init_(self, name, age):
    self.name = name
    self.age = age

DB_HOST = "localhost"
DB_PORT = "5439"
DB_NAME = "fift"
DB_USER = "postgres"
DB_PASSWORD = "postgres"

# =============================
#   POSTGRESQL TABLE CREATION
# =============================

def create_csr_metadata_table_if_not_exists():
    create_sql = """
    CREATE TABLE IF NOT EXISTS public.csr_metadata (
        id SERIAL PRIMARY KEY,
        symbol TEXT NOT NULL,
        security TEXT NOT NULL,
        year INT NOT NULL,
        region TEXT NOT NULL,
        country TEXT NOT NULL,
        sector TEXT NOT NULL,
        industry TEXT NOT NULL,
        minio_url TEXT NOT NULL,
        UNIQUE(symbol, year)
    );
    """
    try:
        conn = psycopg2.connect(
            host=DB_HOST, port=DB_PORT, dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD
        )
        cursor = conn.cursor()
        cursor.execute(create_sql)
        conn.commit()
        cursor.close()
        conn.close()
        print("✅ csr_metadata table ensured.")
    except Exception as e:
        print(f"❌ Error creating csr_metadata table: {e}")

def create_csr_indicators_table_if_not_exists():
    create_sql = """
    CREATE TABLE IF NOT EXISTS public.csr_indicators (
    id SERIAL PRIMARY KEY,
    symbol TEXT NOT NULL,
    security TEXT NOT NULL,
    year INT NOT NULL,
    region TEXT NOT NULL,
    country TEXT NOT NULL,
    sector TEXT NOT NULL,
    industry TEXT NOT NULL,
    
    scope_1 NUMERIC,
    scope_2 NUMERIC,
    scope_3 NUMERIC,
    total_emissions NUMERIC,

    water_consumption_mcm NUMERIC,
    currency TEXT,
    donation NUMERIC,
    waste_generated_tons NUMERIC,
    renewable_energy_amount_mwh NUMERIC,
    renewable_energy_percentage NUMERIC,
    air_emissions_nox NUMERIC,
    air_emissions_sox NUMERIC,
    air_emissions_voc NUMERIC,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(symbol, year)
);
    """
    try:
        conn = psycopg2.connect(
            host=DB_HOST, port=DB_PORT, dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD
        )
        with conn:
            with conn.cursor() as cur:
                cur.execute(create_sql)
        print("✅ csr_indicators table ensured.")
    except Exception as e:
        print(f"❌ Failed to create csr_indicators table: {e}")

# =============================
#   METADATA VALIDATION SETUP
# =============================

metadata_schema = {
    "type": "object",
    "properties": {
        "symbol": {"type": "string"},
        "security": {"type": "string"},
        "year": {"type": "integer"},
        "region": {"type": "string"},
        "country": {"type": "string"},
        "sector": {"type": "string"},
        "industry": {"type": "string"},
        "minio_url": {"type": "string", "format": "uri"}
    },
    "required": ["symbol", "security", "year", "minio_url"]
}

def validate_metadata(metadata):
    """
    Validates the given metadata dictionary against the defined schema.
    
    Args:
        metadata (dict): Metadata to validate.
        
    Returns:
        bool: True if valid, False otherwise.
    """
    try:
        validate(instance=metadata, schema=metadata_schema)
        return True
    except ValidationError as e:
        print("Invalid metadata:", e)
        return False
    
# =============================
#   CHECK IF REPORT EXISTS
# =============================

def check_if_report_exists(symbol, year):
    """
    Checks if a CSR report for a given symbol & year already exists in PostgreSQL.
    
    Args:
        symbol (str): Stock symbol.
        year (int): Report year.

    Returns:
        bool: True if report exists, False otherwise.
    """
    try:
        conn = psycopg2.connect(
            host=DB_HOST, port=DB_PORT, dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD
        )
        cursor = conn.cursor()

        cursor.execute(
            "SELECT EXISTS (SELECT 1 FROM csr_metadata WHERE symbol = %s AND year = %s)", (symbol, year)
        )
        exists = cursor.fetchone()[0]

        cursor.close()
        conn.close()
        return exists
    except psycopg2.Error as e:
        print(f"❌ PostgreSQL Error: {e}")
        return False

# =============================
#   STORE METADATA
# =============================

def store_metadata_in_postgres(symbol, security, year, region, country, sector, industry, minio_url):
    """
    Stores CSR metadata in PostgreSQL, ensuring no duplicate entries.

    Args:
        symbol (str): Stock symbol.
        security (str): Security name.
        year (int): Report year.
        region (str): Company region.
        country (str): Company country.
        sector (str): Company sector.
        industry (str): Company industry.
        minio_url (str): URL of the stored file in MinIO.
    """
    try:
        conn = psycopg2.connect(
            host=DB_HOST, port=DB_PORT, dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD
        )
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO csr_metadata (symbol, security, year, region, country, sector, industry, minio_url) 
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (symbol, year) DO NOTHING
            """,
            (symbol, security, year, region, country, sector, industry, minio_url),
        )
        conn.commit()

        print(f"✅ Metadata stored for {security} ({year}) in PostgreSQL.")

        cursor.close()
        conn.close()
    except psycopg2.Error as e:
        print(f"❌ Database error: {e}")

# =============================
#   CHECK IF INDICATORS EXIST
# =============================
def indicators_exist(symbol, year):
    """
    Check if indicator data exists for a given company and year in csr_indicators.
    """
    try:
        conn = psycopg2.connect(
            host=DB_HOST, port=DB_PORT, dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD
        )
        cursor = conn.cursor()

        cursor.execute("""
            SELECT 1 FROM csr_indicators
            WHERE symbol = %s AND year = %s
            LIMIT 1;
        """, (symbol, year))

        exists = cursor.fetchone() is not None
        cursor.close()
        conn.close()
        return exists
    except Exception as e:
        print(f"❌ Error checking indicator existence: {e}")
        return False

# =============================
#   STORE INDICATORS
# =============================
def store_indicators_in_postgres(symbol,
                                security,
                                year,
                                region,
                                country,
                                sector,
                                industry,
                                scope1,
                                scope2,
                                scope3,
                                total_emissions,
                                water_con,
                                currency,
                                donation_amt,
                                waste_gen,
                                renewable_mwh,
                                renewable_pct,
                                air_emissions_nox,
                                air_emissions_sox,
                                air_emissions_voc):
    """
    Stores water consumption into csr_indicators table.
    Prevents duplicate entries via (symbol, year) UNIQUE constraint.
    """
    try:
        conn = psycopg2.connect(
            host=DB_HOST, port=DB_PORT, dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD
        )
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO public.csr_indicators (
                symbol, security, year, region, country, sector, industry,
                scope_1, scope_2, scope_3, total_emissions,
                water_consumption_mcm,
                currency,
                donation,
                waste_generated_tons,
                renewable_energy_amount_mwh,
                renewable_energy_percentage,
                air_emissions_nox,
                air_emissions_sox,
                air_emissions_voc
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (symbol, year) DO NOTHING;
        """, (symbol, security, year, region, country, sector, industry, scope1, scope2, scope3, total_emissions, water_con, currency, donation_amt, waste_gen, renewable_mwh, renewable_pct, air_emissions_nox, air_emissions_sox, air_emissions_voc))

        conn.commit()
        cursor.close()
        conn.close()
        print(f" Indicators stored for {security} ({year})")

    except Exception as e:
        print(f"❌ Error storing indicators for {security} ({year}): {e}")