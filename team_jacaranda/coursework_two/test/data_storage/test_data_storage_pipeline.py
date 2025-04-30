"""
Module: main_tests

This module contains unit tests for the main module of the data storage
system. It tests various aspects of the main module's functionality, such 
as reading and writing completed modules, running shell commands, handling 
module execution, and ensuring correct pipeline behavior.

Tests use pytest's monkeypatching and mocking techniques to simulate 
various scenarios and edge cases.

Each function is designed to ensure the main module performs as expected
under different conditions, including success and failure cases.
"""

import pytest
import types
import os
import subprocess
import builtins
import logging
from modules.data_storage import main

def test_read_completed_modules(tmp_path, monkeypatch):
    """
    Test that the read_completed_modules function behaves correctly when 
    the file does or does not exist.

    This test covers two scenarios:
    1. The file does not exist, and an empty set is returned.
    2. The file exists with content, and the set contains module names from 
       the file.

    :param tmp_path: A pytest fixture that provides a temporary directory
                     for creating test files.
    :param monkeypatch: A pytest fixture that allows replacing functions 
                        and attributes for testing purposes.
    """
    # Scenario 1: File does not exist
    fake_path = tmp_path / "no_such_file.txt"
    monkeypatch.setattr(main, "completed_file_path", str(fake_path))
    result = main.read_completed_modules()
    assert result == set()  # Non-existent file should return an empty set

    # Scenario 2: File exists and has content
    file_path = tmp_path / "completed_modules.txt"
    file_path.write_text("moduleA.py\nmoduleB.py\n")
    monkeypatch.setattr(main, "completed_file_path", str(file_path))
    result = main.read_completed_modules()
    assert result == {"moduleA.py", "moduleB.py"}  # Should return set with module names

def test_write_completed_module(tmp_path, monkeypatch):
    """
    Test that the write_completed_module function correctly appends module 
    names to the completed file.

    This test checks if the file is properly written with the module names 
    in the expected order, and that the write operation does not overwrite 
    existing data.

    :param tmp_path: A pytest fixture that provides a temporary directory 
                     for creating test files.
    :param monkeypatch: A pytest fixture that allows replacing functions 
                        and attributes for testing purposes.
    """
    file_path = tmp_path / "completed.txt"
    monkeypatch.setattr(main, "completed_file_path", str(file_path))

    # Ensure the file is empty or does not exist
    if file_path.exists():
        file_path.unlink()

    main.write_completed_module("mod1.py")
    main.write_completed_module("mod2.py")

    # Read file content and verify
    content = file_path.read_text().splitlines()
    assert "mod1.py" in content and "mod2.py" in content
    # Ensure the modules are added in the correct order
    assert content[-2:] == ["mod1.py", "mod2.py"]

def test_run_command_success_and_failure(monkeypatch):
    """
    Test the run_command function for both success and failure scenarios.

    This test simulates a successful command execution and a failed command 
    execution. It verifies that the correct behavior occurs in both cases:
    1. A successful command updates the called command.
    2. A failed command raises a SystemExit exception.

    :param monkeypatch: A pytest fixture that allows replacing functions 
                        and attributes for testing purposes.
    """
    # Simulate successful execution, command should not raise an exception
    called = {"cmd": None}
    monkeypatch.setattr(subprocess, "run", lambda cmd, check, shell: called.update({"cmd": cmd}))
    main.run_command("echo 'hi'")
    assert called["cmd"] == "echo 'hi'"

    # Simulate failed execution, raise CalledProcessError
    def fake_run(cmd, check, shell):
        raise subprocess.CalledProcessError(1, cmd, "Error")
    monkeypatch.setattr(subprocess, "run", fake_run)

    # Capture sys.exit call
    with pytest.raises(SystemExit) as excinfo:
        main.run_command("false")
    assert excinfo.value.code == 1

def test_main_skip_and_execute(monkeypatch):
    """
    Test the main function to ensure that already completed modules are skipped 
    and that the remaining modules are executed in the correct order.

    This test simulates the execution flow of the main function, where it skips 
    already completed modules and runs the remaining modules. It checks the order 
    of execution and ensures that completed modules are not re-executed.

    :param monkeypatch: A pytest fixture that allows replacing functions 
                        and attributes for testing purposes.
    """
    # Simulate some modules being completed
    completed = {"create_table.py", "llm_analyse.py"}
    monkeypatch.setattr(main, "read_completed_modules", lambda: completed)

    # Track executed commands and written modules
    executed_cmds = []
    written_modules = []
    monkeypatch.setattr(main, "run_command", lambda cmd: executed_cmds.append(cmd))
    monkeypatch.setattr(main, "write_completed_module", lambda module: written_modules.append(module))

    # Replace tqdm to avoid actual progress display
    class DummyPbar:
        def __enter__(self): return self
        def __exit__(self, exc_type, exc, tb): return False
        def update(self, n): pass
    monkeypatch.setattr(main, "tqdm", lambda total, desc, ncols: DummyPbar())

    # Run the main function
    main.main()

    # Verify that the first command is for installing dependencies
    assert executed_cmds[0] == "poetry install"

    # Expected order of commands for the remaining modules
    expected_order = [
        "poetry run python modules/data_storage/paragraph_extraction.py",
        "poetry run python modules/data_storage/retry_failed_reports.py",
        "poetry run python modules/data_storage/llm_standardize.py",
        "poetry run python modules/data_storage/data_export.py"
    ]
    assert executed_cmds[1:] == expected_order

    # Ensure completed modules are not in the executed commands
    for mod in completed:
        mod_cmd = f"poetry run python modules/data_storage/{mod}"
        assert mod_cmd not in executed_cmds

    # Ensure write_completed_module was called for unskipped modules
    written_modules_set = set(written_modules)
    expected_written = {"paragraph_extraction.py", "retry_failed_reports.py", "llm_standardize.py", "data_export.py"}
    assert expected_written.issubset(written_modules_set)

def test_main_pipeline_failure(monkeypatch):
    """
    Test that the main function exits with an error when a module fails.

    This test simulates a failure during the execution of a module in the pipeline 
    and ensures that the main function exits immediately when the failure occurs, 
    without executing subsequent modules.

    :param monkeypatch: A pytest fixture that allows replacing functions 
                        and attributes for testing purposes.
    """
    monkeypatch.setattr(main, "read_completed_modules", lambda: set())

    # Track the number of executed commands
    call_count = {"count": 0}
    def fake_run_command(cmd):
        call_count["count"] += 1
        if "paragraph_extraction.py" in cmd:
            raise SystemExit(1)
    monkeypatch.setattr(main, "run_command", fake_run_command)

    monkeypatch.setattr(main, "write_completed_module", lambda module: None)
    monkeypatch.setattr(main, "tqdm", lambda total, desc, ncols: types.SimpleNamespace(__enter__=lambda self: self, __exit__=lambda self, exc_type, exc, tb: False, update=lambda n: None))

    # Capture SystemExit
    with pytest.raises(SystemExit) as excinfo:
        main.main()

    assert excinfo.value.code == 1
    # Verify the count is 2, indicating the first module and the failed module were executed
    assert call_count["count"] == 2
