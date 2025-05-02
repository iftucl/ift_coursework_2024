"""
Unit tests for Pipeline 1: Process Problematic Files
"""

import os
import sys
from pathlib import Path

import pandas as pd
import pytest

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from pipeline1.modules.process_problematic import delete_files, process_problematic_files


def test_delete_files(tmp_path):
    """Test deleting files"""
    # Create test directory structure
    company_dir = tmp_path / "company"
    year_dir = company_dir / "2024"
    os.makedirs(year_dir)

    # Create test files
    test_file = year_dir / "test.pdf"
    test_file.write_text("test content")

    # Create test DataFrame
    files_df = pd.DataFrame(
        {"company": ["company"], "year": [2024], "filename": ["test.pdf"]}
    )

    # Test deletion
    found_count, deleted_count, errors = delete_files(files_df, str(tmp_path))
    assert found_count == 1
    assert deleted_count == 1
    assert not errors
    assert not os.path.exists(test_file)
    assert not os.path.exists(year_dir)
    assert not os.path.exists(company_dir)


def test_delete_files_nonexistent(tmp_path):
    """Test deleting nonexistent files"""
    # Create test DataFrame
    files_df = pd.DataFrame(
        {"company": ["company"], "year": [2024], "filename": ["nonexistent.pdf"]}
    )

    # Test deletion
    found_count, deleted_count, errors = delete_files(files_df, str(tmp_path))
    assert found_count == 1
    assert deleted_count == 0
    assert len(errors) == 1
    assert "File does not exist" in errors[0]


def test_process_problematic_files(tmp_path, monkeypatch):
    """Test processing problematic files"""
    # TODO: Fix path handling
    return
