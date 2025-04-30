"""
This module exports tables from a PostgreSQL database to CSV files.

It uses `psycopg2` for database connectivity and `pandas` to execute SQL queries and export the results 
to CSV files. The module supports configuration for the database connection, output file paths, 
and default sorting columns for the queries.

Functions:
- `export_table_to_csv`: Exports a specified table from the PostgreSQL database to a CSV file.
- `main`: Orchestrates the connection to the database and exports predefined tables to CSV files.
"""

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
    """
    Exports a specific table from the PostgreSQL database to a CSV file.

    This function fetches all data from the specified table, optionally ordering it 
    by a default column (if configured), and saves the results to a CSV file at the 
    provided output path.

    :param table_name: The name of the table to export.
    :type table_name: str
    :param output_path: The path where the CSV file will be saved.
    :type output_path: str
    :param conn: A psycopg2 connection object used to interact with the database.
    :type conn: psycopg2.extensions.connection
    :return: None
    :raises: Any exceptions raised by the `pandas.read_sql_query` or `pandas.DataFrame.to_csv` functions.
    """
    order_col = default_order_columns.get(table_name, None)
    query = f"SELECT * FROM {table_name}"
    if order_col:
        query += f" ORDER BY {order_col}"

    df = pd.read_sql_query(query, conn)
    df.to_csv(output_path, index=False, encoding='utf-8-sig')
    print(f"✅ Table {table_name} has been successfully exported to {output_path}")

# === Main Function ===
def main():
    """
    Main function to connect to the PostgreSQL database and export multiple tables to CSV files.

    This function establishes a connection to the database, iterates over a predefined 
    list of tables, and calls `export_table_to_csv` to export each table to a CSV file.

    :return: None
    :raises: Any exceptions raised during the database connection or table export process.
    """
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
