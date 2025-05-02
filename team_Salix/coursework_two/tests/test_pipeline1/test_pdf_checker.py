"""
Unit tests for Pipeline 1: PDF Checker
"""

import os

import pytest

from pipeline1.modules.pdf_checker import check_pdf_readability


def test_check_pdf_valid(tmp_path):
    """Test checking a valid PDF file"""
    # Create a temporary PDF file with a more realistic structure
    pdf_path = tmp_path / "test.pdf"
    pdf_content = (
        b"%PDF-1.4\n"
        b"1 0 obj\n"
        b"<<\n"
        b"/Type /Catalog\n"
        b"/Pages 2 0 R\n"
        b">>\n"
        b"endobj\n"
        b"2 0 obj\n"
        b"<<\n"
        b"/Type /Pages\n"
        b"/Kids [3 0 R]\n"
        b"/Count 1\n"
        b">>\n"
        b"endobj\n"
        b"3 0 obj\n"
        b"<<\n"
        b"/Type /Page\n"
        b"/Parent 2 0 R\n"
        b"/Resources <<\n"
        b"/Font <<\n"
        b"/F1 4 0 R\n"
        b">>\n"
        b">>\n"
        b"/MediaBox [0 0 612 792]\n"
        b"/Contents 5 0 R\n"
        b">>\n"
        b"endobj\n"
        b"4 0 obj\n"
        b"<<\n"
        b"/Type /Font\n"
        b"/Subtype /Type1\n"
        b"/BaseFont /Helvetica\n"
        b">>\n"
        b"endobj\n"
        b"5 0 obj\n"
        b"<<\n"
        b"/Length 44\n"
        b">>\n"
        b"stream\n"
        b"BT\n"
        b"/F1 24 Tf\n"
        b"100 100 Td\n"
        b"(Test PDF) Tj\n"
        b"ET\n"
        b"endstream\n"
        b"endobj\n"
        b"xref\n"
        b"0 6\n"
        b"0000000000 65535 f\n"
        b"0000000010 00000 n\n"
        b"0000000079 00000 n\n"
        b"0000000173 00000 n\n"
        b"0000000301 00000 n\n"
        b"0000000380 00000 n\n"
        b"trailer\n"
        b"<<\n"
        b"/Size 6\n"
        b"/Root 1 0 R\n"
        b">>\n"
        b"startxref\n"
        b"492\n"
        b"%%EOF\n"
    )
    pdf_path.write_bytes(pdf_content)

    is_readable, message = check_pdf_readability(str(pdf_path))
    assert is_readable
    assert "readable" in message.lower()


def test_check_pdf_invalid(tmp_path):
    """Test checking an invalid PDF file"""
    # Create an invalid PDF file
    invalid_pdf = tmp_path / "invalid.pdf"
    invalid_pdf.write_text("This is not a PDF file")

    is_readable, message = check_pdf_readability(str(invalid_pdf))
    assert not is_readable
    assert "error" in message.lower()


def test_check_pdf_nonexistent():
    """Test checking a non-existent file"""
    is_readable, message = check_pdf_readability("nonexistent.pdf")
    assert not is_readable
    assert "error" in message.lower()


def test_check_pdf_empty(tmp_path):
    """Test checking an empty file"""
    empty_pdf = tmp_path / "empty.pdf"
    empty_pdf.write_bytes(b"")

    is_readable, message = check_pdf_readability(str(empty_pdf))
    assert not is_readable
    assert "error" in message.lower()


def test_check_pdf_corrupted(tmp_path):
    """Test checking a corrupted PDF file"""
    corrupted_pdf = tmp_path / "corrupted.pdf"
    corrupted_pdf.write_bytes(b"%PDF-1.4\nThis is a corrupted PDF file")

    is_readable, message = check_pdf_readability(str(corrupted_pdf))
    assert not is_readable
    assert "error" in message.lower()
