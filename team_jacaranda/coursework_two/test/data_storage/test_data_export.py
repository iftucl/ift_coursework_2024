"""
Module: data_export_tests

This module contains test functions for testing the functionalities
of the data export module in the `data_export` package. It tests
the SQL query formation for exporting tables, the export process,
and the correct execution of the `main()` function.

The tests mock dependencies like the database connection and pandas
DataFrame methods to validate the correct behavior of the export logic.
"""

import types
import pandas as pd
from modules.data_storage import data_export

def test_export_table_query_with_order(monkeypatch):
    """
    Test that the query string correctly appends the ORDER BY clause 
    when there are default order columns.

    This test simulates the execution of a query with a default order 
    column (e.g., "ORDER BY id") and verifies that the `export_table_to_csv` 
    function appends the ORDER BY clause in the query. It also checks if the 
    query is correctly passed to the pandas `read_sql_query` function and if 
    the `to_csv` method is invoked with the correct path.

    :param monkeypatch: The monkeypatch fixture provided by pytest.
    """
    captured_query = {}
    # Simulate pandas.read_sql_query to capture the SQL query
    def fake_read_sql(query, conn):
        captured_query["sql"] = query
        # Return an empty DataFrame
        return pd.DataFrame()
    monkeypatch.setattr(data_export, "pd", types.SimpleNamespace(read_sql_query=fake_read_sql, DataFrame=pd.DataFrame))
    # Simulate DataFrame.to_csv method to record output path
    output_path = "dummy_path.csv"
    called = {"to_csv": False, "path": None}
    def fake_to_csv(self, path, index=False, encoding=None):
        called["to_csv"] = True
        called["path"] = path
    # Replace DataFrame.to_csv globally for all instances
    monkeypatch.setattr(pd.DataFrame, "to_csv", fake_to_csv, raising=False)
    # Use table in default_order_columns to call the function
    table_name = "csr_reporting.company_reports"
    data_export.export_table_to_csv(table_name, output_path, conn="DummyConnection")
    # Verify that the query contains the ORDER BY clause with the id column
    assert "ORDER BY id" in captured_query["sql"]
    # Verify that to_csv was called with the correct path
    assert called["to_csv"] is True and called["path"] == output_path

def test_export_table_query_without_order(monkeypatch):
    """
    Test that the query string does not include the ORDER BY clause 
    when there are no default order columns.

    This test simulates the execution of a query without a default order 
    column and ensures that the `export_table_to_csv` function does not 
    append the ORDER BY clause to the query. It also checks that the 
    `to_csv` method is still called correctly.

    :param monkeypatch: The monkeypatch fixture provided by pytest.
    """
    captured_query = {}
    monkeypatch.setattr(data_export, "pd", types.SimpleNamespace(
        read_sql_query=lambda q, conn: (captured_query.update({"sql": q}) or pd.DataFrame()),
        DataFrame=pd.DataFrame))
    # Simulate replacing DataFrame.to_csv
    monkeypatch.setattr(pd.DataFrame, "to_csv", lambda self, path, **kwargs: None, raising=False)
    # Call a table not in default_order_columns
    table_name = "some_schema.unknown_table"
    data_export.export_table_to_csv(table_name, "out.csv", conn="DummyConn")
    # Verify that the query does not contain the ORDER BY clause
    assert "ORDER BY" not in captured_query["sql"]

def test_main_exports_all_tables(monkeypatch):
    """
    Test the main() function to ensure it exports all tables in order 
    and closes the connection.

    This test simulates the process of exporting all tables by calling 
    the `main` function and verifies that all expected tables are exported. 
    It also ensures that the database connection is closed after the export 
    process is complete.

    :param monkeypatch: The monkeypatch fixture provided by pytest.
    """
    # Simulate psycopg2.connect returning a DummyConn with close() method
    closed_flag = {"closed": False}
    class DummyConn:
        def close(self):
            closed_flag["closed"] = True
    monkeypatch.setattr(data_export.psycopg2, "connect", lambda **kwargs: DummyConn())
    # Simulate export_table_to_csv to track called tables
    exported_tables = []
    monkeypatch.setattr(data_export, "export_table_to_csv",
                        lambda table, path, conn: exported_tables.append(table))
    # Call the main function
    data_export.main()
    # The list of tables in modules should be exported
    expected_tables = ["csr_reporting.company_reports", "csr_reporting.csr_indicators", "csr_reporting.csr_data"]
    assert exported_tables == expected_tables
    # Verify that the connection is closed
    assert closed_flag["closed"] is True
