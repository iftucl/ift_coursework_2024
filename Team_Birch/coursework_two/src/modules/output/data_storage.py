"""
This script ensures the existence of a PostgreSQL table `csr_reporting.company_indicators`,
creates it if missing, and then loads data from `company_indicators.csv` into the table.

Workflow:
1. Connects to the PostgreSQL database using environment variables from `.env`.
2. Checks if the schema and table exist using `information_schema`.
3. Creates the schema and table if they don't exist.
4. Reads the cleaned CSR indicator data from a CSV file.
5. Standardizes column names for SQL compatibility.
6. Uses SQLAlchemy to insert the DataFrame into PostgreSQL using `to_sql`.
"""

import os

import pandas as pd
import psycopg2
from dotenv import load_dotenv
from sqlalchemy import create_engine

load_dotenv()


schema_name = "csr_reporting"
table_name = "company_indicators"

check_table_exists_query = """
SELECT EXISTS (
    SELECT 1 
    FROM information_schema.tables 
    WHERE table_schema = 'csr_reporting' 
    AND table_name = 'company_indicators'
);
"""

conn = psycopg2.connect(
    dbname=os.getenv("DB_NAME"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    host=os.getenv("DB_HOST"),
    port=os.getenv("DB_PORT"),
)

cur = conn.cursor()

# Check if the table exists
cur.execute(check_table_exists_query)
table_exists = cur.fetchone()[0]
if table_exists:
    print("Table csr_reporting.company_indicators already exists.")
else:
    cur.execute(
        """
    CREATE SCHEMA IF NOT EXISTS csr_reporting;

    CREATE TABLE IF NOT EXISTS csr_reporting.company_indicators (
        company TEXT,
        year INT,
        annual_carbon_emissions_tonnes_CO2 FLOAT,
        annual_water_use_cubic_meters FLOAT,
        renewable_energy_use_MWh FLOAT,
        sustainable_materials_ratio_percent FLOAT,
        waste_recycling_rate_percent FLOAT,
        PRIMARY KEY (company, year)
    );
    """
    )


conn.commit()


engine = create_engine(
    f'postgresql+psycopg2://{os.getenv("DB_USER")}:{os.getenv("DB_PASSWORD")}@'
    f'{os.getenv("DB_HOST")}:{os.getenv("DB_PORT")}/{os.getenv("DB_NAME")}'
)

csv_path = "company_indicators.csv"
df = pd.read_csv(csv_path)
df.columns = [
    "company",
    "year",
    "annual_carbon_emissions_tonnes_co2",
    "annual_water_use_cubic_meters",
    "renewable_energy_use_mwh",
    "sustainable_materials_ratio_percent",
    "waste_recycling_rate_percent",
]

df.to_sql(
    name=table_name,
    schema=schema_name,
    con=engine,
    if_exists="append",  # Append data
    index=False,  # Do not insert the DataFrame index column
)

print("Data inserted successfully.")

cur.close()
conn.close()
