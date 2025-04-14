import os
import pandas as pd
import psycopg2

# === Database Configuration ===
db_config = {
    "dbname": "fift",
    "user": "postgres",
    "password": "postgres",
    "host": "host.docker.internal",
    "port": 5439
}

# === Export Path Settings: modules/db Directory ===
script_dir = os.path.dirname(__file__)  # Path where the current script is located (modules/data_storage)
output_dir = os.path.abspath(os.path.join(script_dir, "../db"))  # Go back to modules, then into db
os.makedirs(output_dir, exist_ok=True)

# === Default Sorting Column Settings ===
default_order_columns = {
    "csr_reporting.company_reports": "id",
    "csr_reporting.csr_indicators": "indicator_id",
    "csr_reporting.csr_data": "data_id"
}

# === Export Function ===
def export_table_to_csv(table_name, output_path, conn):
    order_col = default_order_columns.get(table_name, None)
    query = f"SELECT * FROM {table_name}"
    if order_col:
        query += f" ORDER BY {order_col}"

    df = pd.read_sql_query(query, conn)
    df.to_csv(output_path, index=False, encoding='utf-8-sig')
    print(f"✅ Table {table_name} has been successfully exported to {output_path}")

# === Main Function ===
def main():
    conn = psycopg2.connect(**db_config)
    try:
        table_list = [
            ("csr_reporting.company_reports", os.path.join(output_dir, "company_reports.csv")),
            ("csr_reporting.csr_indicators", os.path.join(output_dir, "csr_indicators.csv")),
            ("csr_reporting.csr_data", os.path.join(output_dir, "csr_data.csv")),
        ]

        for table_name, csv_path in table_list:
            export_table_to_csv(table_name, csv_path, conn)

    finally:
        conn.close()

if __name__ == "__main__":
    main()
