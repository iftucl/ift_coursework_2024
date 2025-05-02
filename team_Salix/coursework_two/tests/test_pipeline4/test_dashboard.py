"""
Unit tests for Pipeline 4: Dashboard and Visualization
"""

import os
import sys
from pathlib import Path

import pandas as pd
import pytest
from sqlalchemy import text

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from pipeline4.modules.dashboard import load_esg_data, load_lineage_data


def test_load_esg_data(db_engine):
    """Test loading ESG data from database"""
    # Insert test data
    with db_engine.connect() as conn:
        conn.execute(
            text(
                """
            CREATE SCHEMA IF NOT EXISTS csr_reporting;
            DROP TABLE IF EXISTS csr_reporting.esg_indicators;
            CREATE TABLE csr_reporting.esg_indicators (
                company VARCHAR(255),
                year INTEGER,
                scope1_emissions FLOAT,
                scope2_emissions FLOAT,
                total_energy_consumption FLOAT,
                total_water_withdrawal FLOAT,
                total_waste_generated FLOAT,
                employee_diversity FLOAT
            );
            INSERT INTO csr_reporting.esg_indicators VALUES
            ('Test Corp', 2023, 100.0, 200.0, 1000.0, 5000.0, 300.0, 45.0);
        """
            )
        )
        conn.commit()

    # Load data
    df = load_esg_data()
    assert not df.empty
    assert "company" in df.columns
    assert len(df) > 0


def test_load_lineage_data(db_engine):
    """Test loading data lineage from database"""
    # Insert test data
    with db_engine.connect() as conn:
        conn.execute(
            text(
                """
            CREATE SCHEMA IF NOT EXISTS csr_reporting;
            DROP TABLE IF EXISTS csr_reporting.data_lineage;
            CREATE TABLE csr_reporting.data_lineage (
                step VARCHAR(255),
                script VARCHAR(255),
                input VARCHAR(255),
                output VARCHAR(255)
            );
            INSERT INTO csr_reporting.data_lineage VALUES
            ('Download', 'download.py', 'URL', 'PDF');
        """
            )
        )
        conn.commit()

    # Load data
    df = load_lineage_data()
    assert not df.empty
    assert "step" in df.columns
    assert len(df) > 0


@pytest.mark.integration
def test_complete_dashboard_pipeline(db_engine):
    """Integration test for the complete dashboard pipeline"""
    # Insert test data
    with db_engine.connect() as conn:
        conn.execute(
            text(
                """
            CREATE SCHEMA IF NOT EXISTS csr_reporting;
            
            DROP TABLE IF EXISTS csr_reporting.esg_indicators;
            CREATE TABLE csr_reporting.esg_indicators (
                company VARCHAR(255),
                year INTEGER,
                scope1_emissions FLOAT,
                scope2_emissions FLOAT,
                total_energy_consumption FLOAT,
                total_water_withdrawal FLOAT,
                total_waste_generated FLOAT,
                employee_diversity FLOAT
            );
            INSERT INTO csr_reporting.esg_indicators VALUES
            ('Test Corp', 2023, 100.0, 200.0, 1000.0, 5000.0, 300.0, 45.0);
            
            DROP TABLE IF EXISTS csr_reporting.data_lineage;
            CREATE TABLE csr_reporting.data_lineage (
                step VARCHAR(255),
                script VARCHAR(255),
                input VARCHAR(255),
                output VARCHAR(255)
            );
            INSERT INTO csr_reporting.data_lineage VALUES
            ('Download', 'download.py', 'URL', 'PDF');
        """
            )
        )
        conn.commit()

    # Load both datasets
    esg_df = load_esg_data()
    lineage_df = load_lineage_data()

    # Verify data
    assert not esg_df.empty
    assert not lineage_df.empty
    assert "company" in esg_df.columns
    assert "step" in lineage_df.columns


@pytest.mark.integration
def test_data_visualization_preparation():
    """Test data preparation for visualization"""
    try:
        esg_df = pd.DataFrame(
            {
                "company": ["Company A", "Company B"],
                "year": [2023, 2023],
                "scope1_emissions": [100.0, 150.0],
            }
        )

        # Test basic DataFrame operations used in visualization
        companies = sorted(esg_df["company"].unique())
        years = sorted(esg_df["year"].unique())

        assert len(companies) == 2
        assert len(years) == 1
        assert isinstance(companies, list)
        assert isinstance(years, list)
    except Exception as e:
        pytest.fail(f"Visualization preparation test failed: {str(e)}")
