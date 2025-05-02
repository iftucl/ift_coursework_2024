from unittest import mock

import pandas as pd
import pytest


@mock.patch("psycopg2.connect")
@mock.patch("pandas.read_sql")
def test_export_and_merge(mock_read_sql, mock_connect):
    mock_conn = mock.MagicMock()
    mock_connect.return_value = mock_conn

    df1 = pd.DataFrame(
        {
            "symbol": ["AAA"],
            "security": ["Test Inc"],
            "report_url": ["url"],
            "report_year": [2022],
        }
    )
    df2 = pd.DataFrame({"symbol": ["AAA"], "security": ["Test Inc"]})

    mock_read_sql.side_effect = [df1, df2]

    from modules.output import data_export  # Force script run

    assert isinstance(data_export.df1_cleaned, pd.DataFrame)
    assert isinstance(data_export.df, pd.DataFrame)
