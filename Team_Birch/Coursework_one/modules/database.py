import psycopg2

DB_SETTINGS = {
    "host": "localhost",
    "port": 5439,
    "dbname": "fift",
    "user": "postgres",
    "password": "postgres"
}

def has_existing_table(cur):
    query = (
        "SELECT EXISTS ("
        " SELECT FROM information_schema.tables"
        " WHERE table_schema = 'csr_reporting'"
        " AND table_name = 'company_reports'"
        ")"
    )
    cur.execute(query)
    return bool(cur.fetchone()[0])

def setup_table(cur):
    cur.execute(
        "CREATE TABLE csr_reporting.company_reports ("
        " id SERIAL PRIMARY KEY,"
        " symbol CHAR(12),"
        " security TEXT,"
        " report_url VARCHAR(255),"
        " report_year INTEGER,"
        " minio_path VARCHAR(255)"
        ")"
    )

def insert_seed_data(cur):
    cur.execute("SELECT symbol, security FROM csr_reporting.company_static ORDER BY symbol")
    for row in cur.fetchall():
        cur.execute(
            "INSERT INTO csr_reporting.company_reports (symbol, security) "
            "VALUES (%s, %s) ON CONFLICT DO NOTHING",
            row
        )

def main():
    connection = None
    try:
        connection = psycopg2.connect(**DB_SETTINGS)
        cur = connection.cursor()

        if not has_existing_table(cur):
            setup_table(cur)
            insert_seed_data(cur)

        connection.commit()
    except Exception as error:
        print("Error during execution:", error)
    finally:
        if connection:
            cur.close()
            connection.close()

if __name__ == "__main__":
    main()
