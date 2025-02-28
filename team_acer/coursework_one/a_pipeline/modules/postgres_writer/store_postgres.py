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