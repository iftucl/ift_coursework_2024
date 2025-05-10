import psycopg2
from config import DB_CONFIG


def get_connection():
    return psycopg2.connect(**DB_CONFIG)


def create_reports_with_indicators():
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

    finally:
        # Close connection in finally block
        cursor.close()
        conn.close()


if __name__ == "__main__":
    create_reports_with_indicators()