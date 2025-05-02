import importlib
from unittest import mock

import pandas as pd
import pytest


@pytest.fixture
def dummy_df():
    return pd.DataFrame(
        {
            "company": ["A"],
            "year": [2022],
            "annual_carbon_emissions_tonnes_co2": [1.0],
            "annual_water_use_cubic_meters": [2.0],
            "renewable_energy_use_mwh": [3.0],
            "sustainable_materials_ratio_percent": [4.0],
            "waste_recycling_rate_percent": [5.0],
        }
    )


@mock.patch("pandas.read_csv")
@mock.patch("sqlalchemy.create_engine")
@mock.patch("psycopg2.connect")
def test_table_exists_path(mock_connect, mock_create_engine, mock_read_csv, dummy_df):
    mock_conn = mock.MagicMock()
    mock_cursor = mock.MagicMock()
    mock_cursor.fetchone.return_value = [True]
    mock_conn.cursor.return_value = mock_cursor
    mock_connect.return_value = mock_conn
    mock_read_csv.return_value = dummy_df

    import modules.output.data_storage as ds

    importlib.reload(ds)

    mock_cursor.execute.assert_called()
    mock_conn.commit.assert_called()


@mock.patch("pandas.read_csv")
@mock.patch("sqlalchemy.create_engine")
@mock.patch("psycopg2.connect")
def test_table_creation_path(mock_connect, mock_create_engine, mock_read_csv, dummy_df):
    mock_conn = mock.MagicMock()
    mock_cursor = mock.MagicMock()
    mock_cursor.fetchone.return_value = [False]
    mock_conn.cursor.return_value = mock_cursor
    mock_connect.return_value = mock_conn
    mock_read_csv.return_value = dummy_df

    import modules.output.data_storage as ds

    importlib.reload(ds)

    assert mock_cursor.execute.call_count >= 2
    mock_conn.commit.assert_called()
