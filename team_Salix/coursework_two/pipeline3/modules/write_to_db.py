"""
ESG Data Database Writer

This script loads ESG indicators from a CSV file and writes them to a PostgreSQL database.
It includes data cleaning, type conversion, and error handling for database operations.

The script performs the following operations:
1. Connects to the PostgreSQL database
2. Reads ESG indicators from a CSV file
3. Cleans and standardizes the data
4. Writes the processed data to the database

Note:
    - The CSV file should be located at 'logs/esg_indicators.csv'
    - Database connection details are configured in the script
    - The data is written to the 'csr_reporting' schema
"""

import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError
from pandas.errors import EmptyDataError
from psycopg2 import OperationalError


def write_esg_to_db():
    """
    Write ESG indicators from CSV to PostgreSQL database.

    This function:
    1. Establishes a connection to the PostgreSQL database
    2. Reads and processes the ESG indicators CSV file
    3. Performs data cleaning and type conversion
    4. Writes the processed data to the database
    5. Handles various exceptions and provides appropriate error messages

    The function performs the following data processing steps:
    - Renames columns to match database schema
    - Converts 'N/A' and empty values to NULL
    - Converts numeric values to appropriate types
    - Handles type conversion errors gracefully

    Raises:
        FileNotFoundError: If the CSV file is not found
        EmptyDataError: If the CSV file is empty
        OperationalError: If there are database connection issues
        SQLAlchemyError: If there are database operation errors
        Exception: For any other unexpected errors

    Note:
        The function automatically disposes of the database connection
        when finished, regardless of success or failure.
    """
    try:
        # Set PostgreSQL connection information
        db_config = {
            "host": "localhost",
            "port": 5439,
            "database": "fift",
            "user": "postgres",
            "password": "postgres",
        }

        # Create engine using SQLAlchemy
        engine = create_engine(
            f"postgresql+psycopg2://{db_config['user']}:{db_config['password']}@"
            f"{db_config['host']}:{db_config['port']}/{db_config['database']}"
        )

        # Read CSV file
        df = pd.read_csv("logs/esg_indicators.csv")

        # Column name mapping
        column_mapping = {
            "Company Name": "company",
            "Year": "year",
            "Scope 1 Emissions (tCO2e)": "scope1_emissions",
            "Scope 2 Emissions (tCO2e)": "scope2_emissions",
            "Total Energy Consumption (MWh)": "total_energy_consumption",
            "Total Water Withdrawal (m³)": "total_water_withdrawal",
            "Total Waste Generated (Metric tons)": "total_waste_generated",
            "Employee Diversity (%)": "employee_diversity",
        }
        df.rename(columns=column_mapping, inplace=True)
        df = df[list(column_mapping.values())]

        # Standardize handling of N/A, empty strings as None, and perform type conversion
        def clean_value(val, dtype="float"):
            if pd.isna(val) or str(val).strip().upper() == "N/A" or str(val).strip() == "":
                return None
            if dtype == "int":
                try:
                    return int(float(val))
                except (ValueError, TypeError):
                    return None
            if dtype == "float":
                try:
                    return float(val)
                except (ValueError, TypeError):
                    return None
            return str(val).strip()

        df["year"] = df["year"].apply(lambda x: clean_value(x, "int"))
        for col in [
            "scope1_emissions",
            "scope2_emissions",
            "total_energy_consumption",
            "total_water_withdrawal",
            "total_waste_generated",
            "employee_diversity",
        ]:
            df[col] = df[col].apply(lambda x: clean_value(x, "float"))

        # Write to PostgreSQL (schema: csr_reporting)
        df.to_sql(
            "esg_indicators",
            engine,
            schema="csr_reporting",
            if_exists="replace",
            index=False,
        )

        print("✅ ESG indicators successfully written to PostgreSQL.")
    except FileNotFoundError:
        print("❌ Error: CSV file not found at 'logs/esg_indicators.csv'")
    except EmptyDataError:
        print("❌ Error: CSV file is empty")
    except OperationalError as e:
        print(f"❌ Database connection error: {e}")
    except SQLAlchemyError as e:
        print(f"❌ Database operation error: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
    finally:
        if 'engine' in locals():
            engine.dispose()


if __name__ == "__main__":
    write_esg_to_db()
