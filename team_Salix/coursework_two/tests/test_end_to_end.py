"""
End-to-End Tests for Complete CSR Pipeline
"""

import os
import sys
from pathlib import Path

import pandas as pd
import pytest
from sqlalchemy import text as sql_text

# Add project root directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from pipeline1.modules.main import PDFDownloader
from pipeline2.modules.modelv2 import extract_text_from_pdf, process_esg_data
from pipeline3.modules.write_lineage import write_data_lineage_to_db
from pipeline4.modules.dashboard import load_esg_data, load_lineage_data


@pytest.mark.e2e
def test_complete_pipeline(db_engine, sample_pdf_path, tmp_path):
    """Test the complete pipeline from PDF download to dashboard data"""
    try:
        # Step 1: PDF Download
        downloader = PDFDownloader()
        pdf_path = tmp_path / "test.pdf"
        with open(sample_pdf_path, "rb") as src, open(pdf_path, "wb") as dst:
            dst.write(src.read())
        assert os.path.exists(pdf_path)

        # Step 2: Text Extraction
        extracted_text = extract_text_from_pdf(pdf_path)
        assert isinstance(extracted_text, str)
        assert len(extracted_text) > 0

        # Step 3: Database Writing
        # Create schema
        with db_engine.connect() as conn:
            conn.execute(sql_text("CREATE SCHEMA IF NOT EXISTS csr_reporting"))
            conn.commit()

        # Write ESG data
        mock_esg_data = pd.DataFrame(
            {
                "company": ["Test Corp"],
                "year": [2023],
                "scope1_emissions": [100.0],
                "scope2_emissions": [200.0],
                "total_energy_consumption": [1000.0],
                "total_water_withdrawal": [5000.0],
                "total_waste_generated": [300.0],
                "employee_diversity": [45.0],
            }
        )

        mock_esg_data.to_sql(
            "esg_indicators",
            db_engine,
            schema="csr_reporting",
            if_exists="replace",
            index=False,
        )

        # Write lineage data
        write_data_lineage_to_db()

        # Step 4: Dashboard Data Loading
        esg_df = load_esg_data()
        lineage_df = load_lineage_data()

        assert not esg_df.empty
        assert not lineage_df.empty
        assert "company" in esg_df.columns
        assert "Step" in lineage_df.columns

    except Exception as e:
        pytest.fail(f"End-to-end test failed: {str(e)}")


@pytest.mark.e2e
def test_data_consistency(db_engine):
    """Test data consistency across the pipeline"""
    try:
        # Query both tables
        esg_data = pd.read_sql("SELECT * FROM csr_reporting.esg_indicators", db_engine)
        lineage_data = pd.read_sql(
            "SELECT * FROM csr_reporting.data_lineage", db_engine
        )

        # Verify data integrity
        assert not esg_data.empty, "ESG data should not be empty"
        assert not lineage_data.empty, "Lineage data should not be empty"

        # Check for required columns
        assert all(
            col in esg_data.columns
            for col in ["company", "year", "scope1_emissions", "scope2_emissions"]
        ), "Missing required ESG columns"

        assert all(
            col in lineage_data.columns for col in ["Step", "Script", "Input", "Output"]
        ), "Missing required lineage columns"

    except Exception as e:
        pytest.fail(f"Data consistency test failed: {str(e)}")
