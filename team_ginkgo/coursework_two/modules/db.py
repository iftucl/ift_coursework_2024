"""
This module provides functions to interact with the PostgreSQL database.
It includes functions to establish a connection and create/update tables.
"""

import psycopg2
from config import DB_CONFIG


def get_connection():
    """
    Establishes a connection to the PostgreSQL database.

    :return: A connection object to the database.
    :rtype: psycopg2.extensions.connection
    """
    return psycopg2.connect(**DB_CONFIG)


def create_reports_with_indicators():
    """
    Creates or updates the 'csr_reports_with_indicators' table in the database.
    The table is created if it doesn't exist, and additional columns for indicators are added if they don't exist.
    Default units are set for the indicators if not already defined.

    :raises Exception: If an error occurs during the database operations.
    """
    conn = get_connection()
    cursor = conn.cursor()

    try:
        # Create a new table csr_reports_with_indicators if not exists
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ginkgo.csr_reports_with_indicators AS
            SELECT * FROM ginkgo.csr_reports;
        """)
        conn.commit()

        # Add indicators if not exist
        cursor.execute("""
            ALTER TABLE ginkgo.csr_reports_with_indicators
            ADD COLUMN IF NOT EXISTS scope_1 FLOAT,
            ADD COLUMN IF NOT EXISTS scope_1_unit VARCHAR(100),
            ADD COLUMN IF NOT EXISTS scope_2 FLOAT,
            ADD COLUMN IF NOT EXISTS scope_2_unit VARCHAR(100),
            ADD COLUMN IF NOT EXISTS scope_3 FLOAT,
            ADD COLUMN IF NOT EXISTS scope_3_unit VARCHAR(100),
            ADD COLUMN IF NOT EXISTS water_consumption FLOAT,
            ADD COLUMN IF NOT EXISTS water_consumption_unit VARCHAR(100);
        """)
        conn.commit()

        # Set default unit
        cursor.execute("""
            UPDATE ginkgo.csr_reports_with_indicators
            SET scope_1_unit = 'tCO2'
            WHERE scope_1_unit IS NULL;

            UPDATE ginkgo.csr_reports_with_indicators
            SET scope_2_unit = 'tCO2'
            WHERE scope_2_unit IS NULL;
            
            UPDATE ginkgo.csr_reports_with_indicators
            SET scope_3_unit = 'tCO2'
            WHERE scope_3_unit IS NULL;
            
            UPDATE ginkgo.csr_reports_with_indicators
            SET water_consumption_unit = 'Mgal'
            WHERE water_consumption_unit IS NULL;
        """)
        conn.commit()

    except Exception as e:
        # Rollback when exception occurs
        conn.rollback()
        raise e

    finally:
        # Close connection in finally block
        cursor.close()
        conn.close()


if __name__ == "__main__":
    create_reports_with_indicators()