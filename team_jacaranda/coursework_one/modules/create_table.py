import psycopg2

# PostgreSQL database connection configuration
db_config = {
    "dbname": "fift",
    "user": "postgres",
    "password": "postgres",
    "host": "host.docker.internal",
    "port": 5439
}

# SQL query to check if the table exists
check_table_exists_query = """
SELECT EXISTS (
    SELECT 1 
    FROM information_schema.tables 
    WHERE table_schema = 'csr_reporting' 
    AND table_name = 'company_reports'
);
"""

# SQL query to create the table
create_table_query = """
CREATE TABLE csr_reporting.company_reports (
    id SERIAL PRIMARY KEY,
    symbol CHAR(12),
    security TEXT,
    report_url VARCHAR(255),
    report_year INTEGER,
    minio_path VARCHAR(255)
);
"""

# Create the table if it doesn't exist
try:
    conn = psycopg2.connect(**db_config)
    cursor = conn.cursor()

    cursor.execute(check_table_exists_query)
    table_exists = cursor.fetchone()[0]

    if table_exists:
        print("✅ Table csr_reporting.company_reports already exists.")
    else:
        cursor.execute(create_table_query)
        conn.commit()
        print("✅ Table csr_reporting.company_reports created successfully.")

except Exception as e:
    print(f"❌ An error occurred: {e}")
finally:
    if conn:
        cursor.close()
        conn.close()
