import os
import pytest
import fitz
from app.services.parser import DocumentParser

samples_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app", "samples")

def test_parse_text_document():
    content = b"# Program Guidelines\n\nSection 1: The applicant must be registered in the UK."
    parsed = DocumentParser.parse(content, "guidelines.txt")
    assert parsed.page_count >= 1
    assert "Section 1" in parsed.full_text
    assert parsed.file_hash == DocumentParser.compute_sha256(content)

def test_parse_pdf_sample():
    pdf_path = os.path.join(samples_dir, "sample_application.pdf")
    assert os.path.exists(pdf_path), "sample_application.pdf not found"
    with open(pdf_path, "rb") as f:
        bytes_data = f.read()

    parsed = DocumentParser.parse(bytes_data, "sample_application.pdf")
    assert parsed.page_count == 2
    assert "EcoFilter" in parsed.full_text

def test_parse_docx_sample():
    docx_path = os.path.join(samples_dir, "sample_guideline.docx")
    assert os.path.exists(docx_path), "sample_guideline.docx not found"
    with open(docx_path, "rb") as f:
        bytes_data = f.read()

    parsed = DocumentParser.parse(bytes_data, "sample_guideline.docx")
    assert parsed.page_count >= 1
    assert "UK CleanTech" in parsed.full_text

def test_empty_document_error():
    with pytest.raises(ValueError, match="Empty document"):
        DocumentParser.parse(b"", "empty.txt")


def test_whitespace_only_text_document_error():
    with pytest.raises(ValueError, match="is empty"):
        DocumentParser.parse(b" \r\n\t", "whitespace.txt")


def test_pdf_without_extractable_text_error():
    pdf = fitz.open()
    pdf.new_page()
    pdf_bytes = pdf.tobytes()
    pdf.close()

    with pytest.raises(ValueError, match="contains no extractable text"):
        DocumentParser.parse(pdf_bytes, "image_only.pdf")


def test_corrupted_docx_error():
    with pytest.raises(ValueError, match="Corrupted or invalid DOCX"):
        DocumentParser.parse(b"not a DOCX archive", "corrupted.docx")

def test_unsupported_file_type_error():
    with pytest.raises(ValueError, match="Unsupported file format"):
        DocumentParser.parse(b"dummy data", "image.png")

def test_corrupted_pdf_error():
    with pytest.raises(ValueError, match="Corrupted or invalid PDF"):
        DocumentParser.parse(b"%PDF-invalid-bytes-header", "corrupted.pdf")

def test_hash_consistency():
    b1 = b"Identical content"
    b2 = b"Identical content"
    assert DocumentParser.compute_sha256(b1) == DocumentParser.compute_sha256(b2)
