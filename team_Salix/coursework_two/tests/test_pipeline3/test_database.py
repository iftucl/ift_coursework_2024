"""
Unit tests for Pipeline 3: Database Operations
"""

import os
import sys
from pathlib import Path

import pandas as pd
import pytest
from sqlalchemy import text

# Add project root directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from pipeline3.modules.write_lineage import write_data_lineage_to_db
from pipeline3.modules.write_to_db import write_esg_to_db


def test_database_connection(db_engine):
    """Test database connection"""
    with db_engine.connect() as conn:
        result = conn.execute(text("SELECT 1")).scalar()
        assert result == 1


def test_esg_data_writing(db_engine, mock_esg_data):
    """Test writing ESG data to database"""
    try:
        # Create database connection
        with db_engine.connect() as conn:
            # Ensure schema exists
            conn.execute(text("CREATE SCHEMA IF NOT EXISTS csr_reporting"))
            conn.commit()

        # Write ESG data
        mock_esg_data.to_sql(
            "esg_indicators",
            db_engine,
            schema="csr_reporting",
            if_exists="replace",
            index=False,
        )

        # Verify data was written
        result = pd.read_sql("SELECT * FROM csr_reporting.esg_indicators", db_engine)
        assert len(result) > 0
        assert "company" in result.columns
    except Exception as e:
        pytest.fail(f"Failed to write ESG data: {str(e)}")


def test_lineage_data_writing(db_engine):
    """Test writing lineage data to database"""
    try:
        # Run write function
        write_data_lineage_to_db()

        # Verify data was written
        result = pd.read_sql("SELECT * FROM csr_reporting.data_lineage", db_engine)
        assert len(result) > 0
        assert "Step" in result.columns
    except Exception as e:
        pytest.fail(f"Failed to write lineage data: {str(e)}")


@pytest.mark.integration
def test_complete_database_pipeline(db_engine, mock_esg_data):
    """Integration test for complete database operations"""
    try:
        # Create database connection
        with db_engine.connect() as conn:
            # Ensure schema exists
            conn.execute(text("CREATE SCHEMA IF NOT EXISTS csr_reporting"))
            conn.commit()

        # Write ESG data
        mock_esg_data.to_sql(
            "esg_indicators",
            db_engine,
            schema="csr_reporting",
            if_exists="replace",
            index=False,
        )

        # Write lineage data
        write_data_lineage_to_db()

        # Verify both tables exist and contain data
        esg_result = pd.read_sql(
            "SELECT * FROM csr_reporting.esg_indicators", db_engine
        )
        lineage_result = pd.read_sql(
            "SELECT * FROM csr_reporting.data_lineage", db_engine
        )

        assert len(esg_result) > 0
        assert len(lineage_result) > 0
    except Exception as e:
        pytest.fail(f"Database pipeline test failed: {str(e)}")
