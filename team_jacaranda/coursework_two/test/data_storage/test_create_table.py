"""
Module to simulate database connection and cursor behavior using dummy objects.
It includes tests for successful table creation, insert failures, and connection failures.
"""

import builtins
import types
from modules.data_storage import create_table

class DummyCursor:
    """
    A dummy cursor class to simulate database cursor behavior for testing purposes.

    Attributes:
        executed_queries (list): A list that records SQL queries that were executed.
    """

    def __init__(self):
        """
        Initializes the DummyCursor instance, setting up an empty query log.
        """
        self.executed_queries = []

    def execute(self, query):
        """
        Simulates executing an SQL query by recording it in the executed_queries list.

        Args:
            query (str): The SQL query to be executed.
        """
        self.executed_queries.append(query)

    def __enter__(self):
        """
        Enter the runtime context for the cursor (context manager support).
        
        Returns:
            DummyCursor: Returns the current DummyCursor instance.
        """
        return self

    def __exit__(self, exc_type, exc, tb):
        """
        Exit the runtime context for the cursor (context manager support).

        Args:
            exc_type (type): The type of exception raised, if any.
            exc (Exception): The exception raised, if any.
            tb (traceback): The traceback object, if an exception was raised.

        Returns:
            bool: Returns False to propagate exceptions.
        """
        return False


class DummyConnection:
    """
    A dummy connection class to simulate database connection behavior for testing purposes.

    Attributes:
        cursor_obj (DummyCursor): The dummy cursor object used for executing queries.
        committed (bool): A flag indicating whether the connection has been committed.
        closed (bool): A flag indicating whether the connection has been closed.
    """

    def __init__(self):
        """
        Initializes the DummyConnection instance with a DummyCursor and sets the connection flags.
        """
        self.cursor_obj = DummyCursor()
        self.committed = False
        self.closed = False

    def cursor(self):
        """
        Returns the cursor object associated with the connection.
        
        Returns:
            DummyCursor: The cursor object for executing queries.
        """
        return self.cursor_obj

    def commit(self):
        """
        Simulates committing a transaction by setting the committed flag to True.
        """
        self.committed = True

    def close(self):
        """
        Simulates closing the connection by setting the closed flag to True.
        """
        self.closed = True


def test_create_table_success(monkeypatch, capsys):
    """
    Test case for successfully creating a table and inserting data.

    Simulates the scenario where the table creation and data insertion
    are successful, and verifies the correct output and connection behavior.

    Args:
        monkeypatch (MonkeyPatch): A pytest fixture to modify functions or objects at runtime.
        capsys (CaptureFixture): A pytest fixture to capture system outputs.
    """
    dummy_conn = DummyConnection()
    # monkeypatch psycopg2.connect to return dummy_conn
    monkeypatch.setattr(create_table.psycopg2, "connect", lambda **kwargs: dummy_conn)
    # monkeypatch execute_values to do nothing to avoid actual insertion
    monkeypatch.setattr(create_table, "execute_values", lambda cursor, sql, data: None)
    # Call the function under test
    create_table.create_table_and_insert_data()
    # Capture and verify success message
    captured = capsys.readouterr().out
    assert "created successfully" in captured  # Verify success message in output
    # Verify commit and close actions
    assert dummy_conn.committed is True
    assert dummy_conn.closed is True


def test_create_table_insert_failure(monkeypatch, capsys):
    """
    Test case for a failure during the data insertion phase.

    Simulates a scenario where data insertion fails, and verifies that the
    appropriate error message is logged and the connection is closed.

    Args:
        monkeypatch (MonkeyPatch): A pytest fixture to modify functions or objects at runtime.
        capsys (CaptureFixture): A pytest fixture to capture system outputs.
    """
    dummy_conn = DummyConnection()
    # monkeypatch psycopg2.connect to return dummy_conn
    monkeypatch.setattr(create_table.psycopg2, "connect", lambda **kwargs: dummy_conn)
    # monkeypatch execute_values to raise an exception during insert
    def raise_error(cursor, sql, data):
        raise Exception("Insert failed")
    monkeypatch.setattr(create_table, "execute_values", raise_error)
    # Call the function under test
    create_table.create_table_and_insert_data()
    captured = capsys.readouterr().out
    # Verify that the error message is logged
    assert "Error occurred" in captured and "Insert failed" in captured
    # Verify that the connection is closed
    assert dummy_conn.closed is True


def test_create_table_connection_failure(monkeypatch, capsys):
    """
    Test case for a database connection failure.

    Simulates a scenario where the database connection fails, and verifies
    that the appropriate error message is logged and the connection is handled correctly.

    Args:
        monkeypatch (MonkeyPatch): A pytest fixture to modify functions or objects at runtime.
        capsys (CaptureFixture): A pytest fixture to capture system outputs.
    """
    # monkeypatch psycopg2.connect to raise an exception
    monkeypatch.setattr(create_table.psycopg2, "connect", lambda **kwargs: (_ for _ in ()).throw(Exception("Conn error")))
    # Call the function under test
    create_table.create_table_and_insert_data()
    captured = capsys.readouterr().out
    # Verify that the connection error message is logged
    assert "Error occurred" in captured and "Conn error" in captured
    # The connection should not be created in this case
    # Ensure that no further actions are performed after the error
    # In this case, the function should exit gracefully without causing further issues.
