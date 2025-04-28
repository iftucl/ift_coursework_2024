"""
Utility script to create and update a metadata table in Postgres for tracking uploaded SQL tables.

Columns:
- table_name: Name of the uploaded table
- schema_name: Schema where the table resides
- num_metrics: Number of metrics in the table
- metric_group: Theme/category of the metrics
- num_companies: Number of companies in the DataFrame
- last_updated: Last updated timestamp
"""

import os
import sys
from loguru import logger
import pandas as pd

sys.path.append(os.path.join(os.path.dirname(__file__), "../.."))

from team_dogwood.coursework_two.src.db_utils.postgres import PostgreSQLDB

def create_metadata_table() -> None:
    """
    Create a metadata table in the PostgreSQL database to track uploaded SQL tables.
    """
    create_schema_query = """
    CREATE SCHEMA IF NOT EXISTS csr_metadata;
    """
    create_table_query = """
    CREATE TABLE IF NOT EXISTS csr_metadata.data_catalogue (
        id SERIAL PRIMARY KEY,
        schema_name TEXT NOT NULL,
        table_name TEXT NOT NULL,
        num_metrics INTEGER,
        metric_group TEXT,
        num_companies INTEGER,
        last_updated TIMESTAMP DEFAULT NOW(),
        UNIQUE (schema_name, table_name)
    );
    """
    with PostgreSQLDB() as db:
        db.execute(create_schema_query)
        db.execute(create_table_query)
        logger.info("metadata table 'csr_metadata.data_catalogue' created or already exists.")

def upsert_metadata_table(
    table_name: str,
    schema_name: str,
    num_metrics: int,
    metric_group: str,
    num_companies: int,
) -> None:
    """
    Upsert (insert or update) the metadata table with information about the uploaded SQL table.

    Args:
        table_name (str): Name of the uploaded table.
        schema_name (str): Schema where the table resides.
        num_metrics (int): Number of metrics in the table.
        metric_group (str): Theme/category of the metrics.
        num_companies (int): Number of companies in the DataFrame.
    """
    upsert_query = """
    INSERT INTO csr_metadata.data_catalogue (
        schema_name, table_name, num_metrics, metric_group, num_companies, last_updated
    ) VALUES (%s, %s, %s, %s, %s, NOW())
    ON CONFLICT (schema_name, table_name) DO UPDATE
    SET
        num_metrics = EXCLUDED.num_metrics,
        metric_group = EXCLUDED.metric_group,
        num_companies = EXCLUDED.num_companies,
        last_updated = NOW();
    """
    with PostgreSQLDB() as db:
        db.execute(
            upsert_query,
            (schema_name, table_name, num_metrics, metric_group, num_companies)
        )
        logger.info(f"Metadata for {schema_name}.{table_name} upserted.")


def get_metadata_table() -> pd.DataFrame:
    """
    Retrieve the metadata table from the PostgreSQL database as a pandas DataFrame.

    Returns:
        pd.DataFrame: DataFrame representing the metadata table.
    """
    select_query = "SELECT * FROM csr_metadata.data_catalogue;"
    with PostgreSQLDB() as db:
        result = db.fetch(select_query)
        # Try to get column names from the first row if it's a dict, else fallback to default columns
        if result and isinstance(result[0], dict):
            df = pd.DataFrame(result)
        else:
            # Fallback: define columns manually if needed
            columns = [
                "id", "schema_name", "table_name", "num_metrics",
                "metric_group", "num_companies", "last_updated"
            ]
            df = pd.DataFrame(result, columns=columns)
        
        logger.info(f"Fetched {len(df)} rows from metadata table.")
        return df
