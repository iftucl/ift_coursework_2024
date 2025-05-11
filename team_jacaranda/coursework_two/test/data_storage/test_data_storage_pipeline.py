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
    """

    # Scenario 1: File does not exist
    fake_path = tmp_path / "no_such_file.txt"
    monkeypatch.setattr(main, "completed_file_path", str(fake_path))
    result = main.read_completed_modules()
    assert result == set()

    # Scenario 2: File exists and has content
    file_path = tmp_path / "completed_modules.txt"
    file_path.write_text("moduleA.py\nmoduleB.py\n")
    monkeypatch.setattr(main, "completed_file_path", str(file_path))
    result = main.read_completed_modules()
    assert result == {"moduleA.py", "moduleB.py"}

def test_write_completed_module(tmp_path, monkeypatch):
    """
    Test that the write_completed_module function correctly appends module 
    names to the completed file.
    """

    file_path = tmp_path / "completed.txt"
    monkeypatch.setattr(main, "completed_file_path", str(file_path))

    if file_path.exists():
        file_path.unlink()

    main.write_completed_module("mod1.py")
    main.write_completed_module("mod2.py")

    content = file_path.read_text().splitlines()
    assert "mod1.py" in content and "mod2.py" in content
    assert content[-2:] == ["mod1.py", "mod2.py"]

def test_run_command_success_and_failure(monkeypatch):
    """
    Test the run_command function for both success and failure scenarios.
    """

    called = {"cmd": None}
    monkeypatch.setattr(subprocess, "run", lambda cmd, check, shell: called.update({"cmd": cmd}))
    main.run_command("echo 'hi'")
    assert called["cmd"] == "echo 'hi'"

    def fake_run(cmd, check, shell):
        raise subprocess.CalledProcessError(1, cmd, "Error")
    monkeypatch.setattr(subprocess, "run", fake_run)

    with pytest.raises(SystemExit) as excinfo:
        main.run_command("false")
    assert excinfo.value.code == 1

def test_main_skip_and_execute(monkeypatch):
    """
    Test the main function to ensure that already completed modules are skipped 
    and that the remaining modules are executed in the correct order.
    """

    completed = {"create_table.py", "llm_analyse.py"}
    monkeypatch.setattr(main, "read_completed_modules", lambda: completed)

    executed_cmds = []
    written_modules = []
    monkeypatch.setattr(main, "run_command", lambda cmd: executed_cmds.append(cmd))
    monkeypatch.setattr(main, "write_completed_module", lambda module: written_modules.append(module))

    class DummyPbar:
        def __enter__(self): return self
        def __exit__(self, exc_type, exc, tb): return False
        def update(self, n): pass
    monkeypatch.setattr(main, "tqdm", lambda total, desc, ncols: DummyPbar())

    main.main()

    assert executed_cmds[0] == "poetry install"

    expected_order = [
        "poetry run python modules/data_storage/paragraph_extraction.py",
        "poetry run python modules/data_storage/retry_failed_reports.py",
        "poetry run python modules/data_storage/llm_standardize.py",
        "poetry run python modules/data_storage/data_export.py"
    ]
    assert executed_cmds[1:] == expected_order

    for mod in completed:
        mod_cmd = f"poetry run python modules/data_storage/{mod}"
        assert mod_cmd not in executed_cmds

    written_modules_set = set(written_modules)
    expected_written = {"paragraph_extraction.py", "retry_failed_reports.py", "llm_standardize.py", "data_export.py"}
    assert expected_written.issubset(written_modules_set)

def test_main_pipeline_failure(monkeypatch):
    """
    Test that the main function exits with an error when a module fails.
    """

    monkeypatch.setattr(main, "read_completed_modules", lambda: set())

    call_count = {"count": 0}
    def fake_run_command(cmd):
        call_count["count"] += 1
        if "paragraph_extraction.py" in cmd:
            raise SystemExit(1)
    monkeypatch.setattr(main, "run_command", fake_run_command)

    monkeypatch.setattr(main, "write_completed_module", lambda module: None)
    monkeypatch.setattr(main, "tqdm", lambda total, desc, ncols: types.SimpleNamespace(
        __enter__=lambda self: self,
        __exit__=lambda self, exc_type, exc, tb: False,
        update=lambda n: None
    ))

    with pytest.raises(SystemExit) as excinfo:
        main.main()

    assert excinfo.value.code == 1
    assert call_count["count"] == 2
