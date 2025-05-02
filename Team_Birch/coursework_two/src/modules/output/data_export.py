"""
This script connects to a PostgreSQL database, exports two tables as CSVs,
cleans and merges them based on company identifiers, and saves the merged output.

Steps:
1. Connects to PostgreSQL using environment variables via `dotenv`.
2. Exports:
    - `csr_reporting.company_reports` to `company_reports.csv`
    - `csr_reporting.company_static` to `company_static.csv`
3. Cleans `symbol` and `security` columns to ensure consistent casing and whitespace.
4. Merges static metadata (`company_static`) with dynamic reports (`company_reports`) on symbol + security.
5. Drops duplicates and saves the final merged data as `company_information.csv`.
"""

import os

import pandas as pd
import psycopg2
from dotenv import load_dotenv

load_dotenv()

conn = psycopg2.connect(
    dbname=os.getenv("DB_NAME"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    host=os.getenv("DB_HOST"),
    port=os.getenv("DB_PORT"),
)


# Export two tables from PostgreSQL
query1 = "SELECT * FROM csr_reporting.company_reports"
df1 = pd.read_sql(query1, conn)

query2 = "SELECT * FROM csr_reporting.company_static"
df2 = pd.read_sql(query2, conn)

df1.to_csv("company_reports.csv", index=False)
df2.to_csv("company_static.csv", index=False)
print("Exported：company_reports.csv")
print("Exported：company_static.csv")

conn.close()

# Process and merge the tables
df1_cleaned = df1.dropna(subset=["report_url", "report_year"])

df1_cleaned = df1_cleaned.copy()
df1_cleaned.loc[:, "symbol"] = df1_cleaned["symbol"].str.strip().str.upper()
df1_cleaned.loc[:, "security"] = df1_cleaned["security"].str.strip()

df2["symbol"] = df2["symbol"].str.strip().str.upper()
df2["security"] = df2["security"].str.strip()

df1_subset = df1_cleaned[["symbol", "security", "report_url", "report_year"]]

merged_df = pd.merge(df2, df1_subset, on=["symbol", "security"], how="left")

df = merged_df.drop_duplicates(subset=["symbol", "security", "report_year"])

# Export the result as a new CSV file
df.to_csv("company_information.csv", index=False)
