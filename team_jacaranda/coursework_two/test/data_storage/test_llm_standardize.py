"""
This module contains tests for the llm_standardize functionality, which includes the processing and standardization
of measurement units using LLM (Large Language Models). It includes dummy database connection and cursor classes to
simulate interactions with a database and test various edge cases, such as invalid or non-convertible data, successful
standardizations, and handling of JSON errors.

Tests cover the following aspects:
- Parsing of JSON wrapped in markdown
- Construction of conversion prompts
- Execution of database updates for standardized data
- Handling of unit mismatches and the conversion process
- Proper handling of success and failure cases for standardization
"""

import pytest
import re
from modules.data_storage import llm_standardize
import json

class DummyCursor:
    """
    A dummy implementation of a database cursor for simulating database interactions.
    """

    def __init__(self):
        """
        Initializes a new instance of the DummyCursor class.
        """
        self.executed = False
        self.last_query = None
        self.last_params = None

    def execute(self, query, params=None):
        """
        Simulates executing a database query.

        Parameters
        ----------
        query : str
            The SQL query string to execute.
        params : dict, optional
            Optional parameters for the SQL query.
        """
        self.executed = True
        self.last_query = query
        self.last_params = params

    def close(self):
        """
        Simulates closing the cursor.
        """
        pass

class DummyConnection:
    """
    A dummy implementation of a database connection, simulating commit, rollback, and cursor functionalities.
    """

    def __init__(self):
        """
        Initializes a new instance of the DummyConnection class.
        """
        self.cursor_obj = DummyCursor()
        self.committed = False
        self.rolled_back = False
        self.closed = False

    def cursor(self):
        """
        Returns the simulated cursor object.

        Returns
        -------
        DummyCursor
            The cursor object for executing queries.
        """
        return self.cursor_obj

    def commit(self):
        """
        Simulates committing the current transaction.
        """
        self.committed = True

    def rollback(self):
        """
        Simulates rolling back the current transaction.
        """
        self.rolled_back = True

    def close(self):
        """
        Simulates closing the database connection.
        """
        self.closed = True

def test_safe_json_parse_cleanup_and_errors():
    """
    Test case for the `safe_json_parse` function to ensure proper handling of valid and invalid JSON strings.
    """
    raw = "```json\n{\"convertibility\": true, \"value_standardized\": \"100\"}\n```"
    parsed = llm_standardize.safe_json_parse(raw)
    assert parsed == {"convertibility": True, "value_standardized": "100"}

    with pytest.raises(ValueError):
        llm_standardize.safe_json_parse("```\n```")

    with pytest.raises(json.JSONDecodeError):
        llm_standardize.safe_json_parse("not a json")

def test_build_conversion_prompt_content():
    """
    Test case for the build_conversion_prompt function to ensure the correct construction of conversion prompts.
    """
    prompt = llm_standardize.build_conversion_prompt(
        "Energy Intensity", "Measures energy usage", "50", "kWh", "kWh"
    )
    assert "indicator is \"Energy Intensity\"" in prompt
    assert "raw value as: 50" in prompt and "original unit: kWh" in prompt
    assert "target unit \"kWh\"" in prompt
    assert "\"convertibility\": true" in prompt

def test_update_standardized_execution(monkeypatch):
    """
    Test case for the update_standardized function to verify SQL execution and commit behavior.
    """
    dummy_conn = DummyConnection()
    llm_standardize.update_standardized(dummy_conn, data_id=5, value_standardized="123", unit_standardized="kg", unit_conversion_note="note")
    cur = dummy_conn.cursor_obj
    assert cur.executed is True
    assert "UPDATE csr_reporting.CSR_Data" in cur.last_query
    assert dummy_conn.committed is True

def test_process_row_unit_match(monkeypatch):
    """
    Test case for the process_row function where the unit matches and no conversion is needed.
    """
    dummy_conn = DummyConnection()
    updated = []
    monkeypatch.setattr(llm_standardize, "update_standardized", lambda conn, did, val, unit, note=None: updated.append((did, val, unit, note)))
    row = (10, "Water Usage", "100", "L", " l ", "desc",)
    result = llm_standardize.process_row(dummy_conn, row)
    assert result == 10
    assert updated and updated[0][:3] == (10, "100", " l ")
    assert "no conversion needed" in updated[0][3]
    assert dummy_conn.rolled_back is False

def test_process_row_convertible_false(monkeypatch):
    """
    Test case for the process_row function when LLM returns a response indicating that conversion is not possible.
    """
    dummy_conn = DummyConnection()
    monkeypatch.setattr(llm_standardize, "call_llm", lambda prompt: '{"convertibility": false, "note": "unsupported"}')
    updated = []
    monkeypatch.setattr(llm_standardize, "update_standardized", lambda conn, did, val, unit, note=None: updated.append((did, val, unit, note)))
    row = (11, "Metric X", "5", "tons", "kg", "desc")
    result = llm_standardize.process_row(dummy_conn, row)
    assert result is None
    assert updated and updated[0][0] == 11 and updated[0][1] is None and updated[0][2] is None
    assert updated[0][3] == "unsupported"
    assert dummy_conn.rolled_back is False

def test_process_row_invalid_result_value(monkeypatch, capsys):
    """
    Test case for the process_row function when the LLM returns a non-numeric value after conversion.
    """
    dummy_conn = DummyConnection()
    monkeypatch.setattr(llm_standardize, "call_llm", lambda prompt: '{"convertibility": true, "value_standardized": "N/A", "note": "not numeric"}')
    row = (12, "Metric Y", "7", "%", "%", "desc")
    result = llm_standardize.process_row(dummy_conn, row)
    assert result is None
    assert dummy_conn.rolled_back is True
    output = capsys.readouterr().out
    assert f"Data ID {row[0]} standardization failed" in output
    assert "N/A" in output

def test_process_row_success(monkeypatch):
    """
    Test case for the process_row function when LLM returns a valid numeric conversion result.
    """
    dummy_conn = DummyConnection()
    monkeypatch.setattr(llm_standardize, "call_llm", lambda prompt: '{"convertibility": true, "value_standardized": "42.0", "note": "OK"}')
    updated = []
    monkeypatch.setattr(llm_standardize, "update_standardized", lambda conn, did, val, unit, note=None: updated.append((did, val, unit, note)))
    row = (13, "Metric Z", "100", "kg", "tons", "desc")
    result = llm_standardize.process_row(dummy_conn, row)
    assert result == 13
    assert updated and updated[0][0] == 13 and updated[0][1] == "42.0" and updated[0][2] == "tons"
    assert dummy_conn.rolled_back is False
    assert dummy_conn.committed is True

def test_main_standardization_pipeline(monkeypatch, capsys):
    """
    Test case for the main function in the standardization pipeline, including bulk processing and file output.
    """
    dummy_conn = DummyConnection()
    monkeypatch.setattr(llm_standardize, "get_connection", lambda: dummy_conn)
    rows = [
        (21, "IndA", "10", "m3", "m3", "descA"),
        (22, "IndB", "5", "kg", "g", "descB")
    ]
    monkeypatch.setattr(llm_standardize, "fetch_rows_to_standardize", lambda conn: rows)
    def fake_process_row(conn, row):
        return row[0] if row[0] == 21 else None
    monkeypatch.setattr(llm_standardize, "process_row", fake_process_row)
    class DummyFuture:
        def __init__(self, result): self._result = result
        def result(self): return self._result
    class DummyExecutor:
        def __enter__(self): return self
        def __exit__(self, exc_type, exc, tb): return False
        def submit(self, func, *args):
            return DummyFuture(func(*args))
    monkeypatch.setattr(llm_standardize, "ThreadPoolExecutor", lambda max_workers=None: DummyExecutor())
    monkeypatch.setattr(llm_standardize, "as_completed", lambda futures, **kwargs: futures)
    monkeypatch.setattr(llm_standardize, "tqdm", lambda iterable=None, **kwargs: iterable if iterable is not None else types.SimpleNamespace(close=lambda: None, update=lambda x: None))
    llm_standardize.main()
    out = capsys.readouterr().out
    assert "2 records need to be standardized" in out
    assert dummy_conn.closed is True
