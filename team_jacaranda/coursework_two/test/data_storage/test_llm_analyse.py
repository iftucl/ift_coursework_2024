"""
Module for testing the LLM (Large Language Model) analysis functions.
This module contains various test cases to ensure the correct behavior of
functions like build_prompt, process_row, update_result, and others in
the llm_analyse module.
"""

import pytest
import json
import builtins
from modules.data_storage import llm_analyse

class DummyCursor:
    """
    A dummy database cursor class to simulate database cursor behavior.
    
    This class is used to simulate cursor behavior for database operations
    during testing, specifically for testing the update_result function.
    """

    def __init__(self):
        """
        Initialize the DummyCursor instance.

        This initializes the cursor state, including flags for query execution 
        and query parameters.
        """
        self.executed = False
        self.last_query = None
        self.last_params = None

    def execute(self, query, params=None):
        """
        Simulate executing a database query.

        Args:
            query (str): The SQL query string to be executed.
            params (tuple): The parameters to be passed to the query.
        """
        self.executed = True
        self.last_query = query
        self.last_params = params

    def __enter__(self):
        """
        Enter the context for the cursor.

        Returns:
            DummyCursor: The current DummyCursor instance.
        """
        return self

    def __exit__(self, exc_type, exc, tb):
        """
        Exit the context for the cursor.

        Args:
            exc_type (Exception): The exception type (if any).
            exc (Exception): The exception instance (if any).
            tb (traceback): The traceback object (if any).

        Returns:
            bool: False to propagate the exception (if any).
        """
        return False


class DummyConnection:
    """
    A dummy database connection class to simulate database connection behavior.
    
    This class is used to simulate database connection operations during testing.
    """

    def __init__(self):
        """
        Initialize the DummyConnection instance.

        This initializes flags for commit, rollback, and connection closure.
        """
        self.committed = False
        self.rolled_back = False
        self.closed = False
        self.cursor_obj = DummyCursor()

    def cursor(self):
        """
        Simulate getting a cursor from the connection.

        Returns:
            DummyCursor: A dummy cursor instance.
        """
        return self.cursor_obj

    def commit(self):
        """
        Simulate committing a transaction.
        """
        self.committed = True

    def rollback(self):
        """
        Simulate rolling back a transaction.
        """
        self.rolled_back = True

    def close(self):
        """
        Simulate closing the connection.
        """
        self.closed = True


def test_build_prompt_target_vs_non_target():
    """
    Test the build_prompt function for target vs non-target classes.
    
    This test verifies that the output prompt varies based on whether the
    target class is specified or not.
    """
    sample_excerpt = [{"page": 5, "text": "Sample paragraph content."}]
    prompt_target = llm_analyse.build_prompt(
        "Carbon Neutrality Target", "Target description", True, sample_excerpt, 2025
    )
    prompt_nontarget = llm_analyse.build_prompt(
        "Carbon Intensity", "Indicator description", False, sample_excerpt, 2025
    )
    assert "goal-oriented" in prompt_target and "multiple sentences allowed" in prompt_target
    assert "numeric value" in prompt_nontarget and "\"unit\"" in prompt_nontarget


def test_is_valid_number():
    """
    Test the is_valid_number function for valid and invalid number inputs.
    
    This test checks if the function correctly identifies valid numeric values
    and handles invalid inputs like strings, None, or empty values.
    """
    assert llm_analyse.is_valid_number("123.45") is True
    assert llm_analyse.is_valid_number("abc") is False
    assert llm_analyse.is_valid_number("") is False
    assert llm_analyse.is_valid_number(None) is False


def test_update_result_executes_commit(monkeypatch):
    """
    Test that the update_result function executes an UPDATE query and commits.
    
    This test verifies that the update_result function correctly executes
    an UPDATE statement and commits the changes to the database.
    
    Args:
        monkeypatch (pytest.MonkeyPatch): The monkeypatch object for mocking.
    """
    dummy_conn = DummyConnection()
    monkeypatch.setattr(llm_analyse, "client", None)
    llm_analyse.update_result(dummy_conn, data_id=1, value_raw="val", unit_raw="unit",
                              llm_response_raw="raw response", pdf_page="1,2")
    assert dummy_conn.cursor_obj.executed is True
    assert "UPDATE csr_reporting.CSR_Data" in dummy_conn.cursor_obj.last_query
    assert dummy_conn.committed is True


def test_process_row_target_json_and_nonjson(monkeypatch):
    """
    Test process_row function with target set to True for both valid and invalid JSON outputs.
    
    This test checks if the function handles cases where the LLM returns valid JSON
    or invalid JSON, and ensures that the appropriate values are passed for updating
    the database.

    Args:
        monkeypatch (pytest.MonkeyPatch): The monkeypatch object for mocking.
    """
    dummy_conn = DummyConnection()
    outputs = [
        '{"value": "Goal achieved"}',  
        'Not a JSON text'             
    ]
    call_count = {"count": 0}
    def fake_call_llm(prompt):
        result = outputs[call_count["count"]]
        call_count["count"] += 1
        return result
    monkeypatch.setattr(llm_analyse, "call_llm", fake_call_llm)
    updated = []
    def fake_update(conn, data_id, value_raw, unit_raw, llm_resp, pages):
        updated.append((data_id, value_raw, unit_raw))
    monkeypatch.setattr(llm_analyse, "update_result", fake_update)
    row = (42, "Target Indicator", [{"page": 1, "text": "para"}], 1, 2025, "desc", True)
    data_id_ret1 = llm_analyse.process_row(dummy_conn, row)
    data_id_ret2 = llm_analyse.process_row(dummy_conn, row)
    assert data_id_ret1 == 42
    assert updated[0][0] == 42 and updated[0][1] == "Goal achieved" and updated[0][2] is None
    assert data_id_ret2 == 42
    assert updated[1][0] == 42 and updated[1][1] == "Not a JSON text" and updated[1][2] is None
    assert dummy_conn.rolled_back is False


def test_process_row_target_non_str_output(monkeypatch):
    """
    Test process_row function with target set to True when LLM outputs a non-string type.
    
    This test ensures that the function correctly handles non-string types like bytes
    and processes them appropriately without errors.
    
    Args:
        monkeypatch (pytest.MonkeyPatch): The monkeypatch object for mocking.
    """
    dummy_conn = DummyConnection()
    monkeypatch.setattr(llm_analyse, "call_llm", lambda prompt: b" Byte response ")
    monkeypatch.setattr(llm_analyse, "update_result", lambda *args, **kwargs: None)
    row = (1, "Some Target", [{"page": 1, "text": "x"}], 1, 2022, "desc", True)
    result = llm_analyse.process_row(dummy_conn, row)
    assert result == 1
    assert dummy_conn.rolled_back is False


def test_process_row_nontarget_invalid_number(monkeypatch):
    """
    Test process_row function with target set to False and invalid number in the LLM output.
    
    This test verifies that the function raises a ValueError and performs a rollback when
    the output is a non-numeric value for a non-target row.
    
    Args:
        monkeypatch (pytest.MonkeyPatch): The monkeypatch object for mocking.
    """
    dummy_conn = DummyConnection()
    monkeypatch.setattr(llm_analyse, "call_llm", lambda prompt: '{"value": "N/A", "unit": "kg"}')
    row = (100, "Indicator", [{"page": 1, "text": "y"}], 1, 2021, "desc", False)
    with pytest.raises(ValueError):
        llm_analyse.process_row(dummy_conn, row)
    assert dummy_conn.rolled_back is True


def test_process_row_nontarget_json_error(monkeypatch):
    """
    Test process_row function with target set to False and invalid JSON format.
    
    This test checks if the function raises a JSONDecodeError when the LLM output is 
    an invalid JSON string and performs a rollback.
    
    Args:
        monkeypatch (pytest.MonkeyPatch): The monkeypatch object for mocking.
    """
    dummy_conn = DummyConnection()
    monkeypatch.setattr(llm_analyse, "call_llm", lambda prompt: "invalid json")
    row = (101, "Indicator2", [{"page": 2, "text": "z"}], 2, 2020, "desc", False)
    with pytest.raises(json.JSONDecodeError):
        llm_analyse.process_row(dummy_conn, row)
    assert dummy_conn.rolled_back is True


def test_main_concurrent_processing(monkeypatch, capsys):
    """
    Test the main function with concurrent processing logic, including both successful 
    and failed tasks.
    
    This test simulates a multi-threaded environment where multiple rows are processed concurrently,
    some successfully and some failing, and verifies the expected output messages.

    Args:
        monkeypatch (pytest.MonkeyPatch): The monkeypatch object for mocking.
        capsys (pytest.CaptureFixture): The capture fixture to capture the standard output.
    """
    dummy_conn = DummyConnection()
    monkeypatch.setattr(llm_analyse, "get_connection", lambda: dummy_conn)
    rows = [
        (1, "Ind1", [], 1, 2020, "desc1", False),
        (2, "Ind2", [], 2, 2021, "desc2", False)
    ]
    monkeypatch.setattr(llm_analyse, "fetch_pending_rows", lambda conn: rows)
    def fake_process_row(conn, row):
        if row[0] == 1:
            return row[0]
        else:
            raise Exception("processing failed")
    monkeypatch.setattr(llm_analyse, "process_row", fake_process_row)
    class DummyFuture:
        def __init__(self, result=None, exception=None):
            self._result = result
            self._exc = exception
        def result(self):
            if self._exc:
                raise self._exc
            return self._result
    class DummyExecutor:
        def __enter__(self): return self
        def __exit__(self, exc_type, exc, tb): return False
        def submit(self, func, *args):
            try:
                res = func(*args)
                return DummyFuture(result=res)
            except Exception as e:
                return DummyFuture(exception=e)
    monkeypatch.setattr(llm_analyse, "ThreadPoolExecutor", lambda max_workers=None: DummyExecutor())
    monkeypatch.setattr(llm_analyse, "as_completed", lambda futures, **kwargs: futures)
    monkeypatch.setattr(llm_analyse, "tqdm", lambda iterable, **kwargs: iterable)
    llm_analyse.main()
    out = capsys.readouterr().out
    assert "Successfully processed" in out
    assert "Processing failed" in out
    assert dummy_conn.closed is True
