import io
import os
import fitz
import pytest
from app.services.parser import DocumentParser, DocumentProcessingError
from app.services.llm_client import MockLLMClient
from app.services.requirement_extractor import RequirementExtractor
from app.models.assessment import Assessment
from app.models.requirement import Requirement
from app.schemas.ai import RequirementExtractionResponse

SAMPLES_DIR = os.path.join(os.path.dirname(__file__), "..", "app", "samples")

def test_extracted_requirements_never_zero_for_valid_guideline(client):
    """1. Upload test guideline, verify requirements >= 1, verify status == 'ANALYZED'"""
    # Create assessment
    res = client.post("/api/assessments", json={
        "grant_name": "Indian Green Innovation Micro-Grant",
        "application_name": "EcoSpark Energy Review"
    })
    assert res.status_code == 201
    asm_id = res.json()["id"]

    # Upload test PDF guideline
    g_path = os.path.join(SAMPLES_DIR, "GrantCheck_Test_Grant_Guideline.pdf")
    with open(g_path, "rb") as f:
        g_bytes = f.read()
    g_res = client.post(
        f"/api/assessments/{asm_id}/documents/upload",
        data={"doc_type": "guideline"},
        files={"file": ("GrantCheck_Test_Grant_Guideline.pdf", io.BytesIO(g_bytes), "application/pdf")}
    )
    assert g_res.status_code == 200

    # Upload test PDF application
    a_path = os.path.join(SAMPLES_DIR, "GrantCheck_Test_Draft_Application.pdf")
    with open(a_path, "rb") as f:
        a_bytes = f.read()
    a_res = client.post(
        f"/api/assessments/{asm_id}/documents/upload",
        data={"doc_type": "application"},
        files={"file": ("GrantCheck_Test_Draft_Application.pdf", io.BytesIO(a_bytes), "application/pdf")}
    )
    assert a_res.status_code == 200

    # Run analysis
    analyze_res = client.post(f"/api/assessments/{asm_id}/analyze")
    assert analyze_res.status_code == 200
    data = analyze_res.json()
    assert data["status"] == "ANALYZED"
    assert len(data["requirements"]) >= 1
    assert data["score"]["total_requirements"] >= 1
    assert data["score"]["total_mandatory"] >= 1

def test_zero_requirements_raises_error(client, db_session, monkeypatch):
    """2. Mock LLM returning 0 requirements, verify status == 'ANALYSIS_FAILED' (or 422 error), verify NOT 'ANALYZED'"""
    res = client.post("/api/assessments", json={"grant_name": "Test Grant", "application_name": "Test App"})
    asm_id = res.json()["id"]

    g_path = os.path.join(SAMPLES_DIR, "GrantCheck_Test_Grant_Guideline.pdf")
    with open(g_path, "rb") as f:
        g_bytes = f.read()
    client.post(
        f"/api/assessments/{asm_id}/documents/upload",
        data={"doc_type": "guideline"},
        files={"file": ("guideline.pdf", io.BytesIO(g_bytes), "application/pdf")}
    )

    a_path = os.path.join(SAMPLES_DIR, "GrantCheck_Test_Draft_Application.pdf")
    with open(a_path, "rb") as f:
        a_bytes = f.read()
    client.post(
        f"/api/assessments/{asm_id}/documents/upload",
        data={"doc_type": "application"},
        files={"file": ("application.pdf", io.BytesIO(a_bytes), "application/pdf")}
    )

    # Force RequirementExtractor.extract to return 0 requirements
    monkeypatch.setattr(RequirementExtractor, "extract", lambda self, doc: [])

    analyze_res = client.post(f"/api/assessments/{asm_id}/analyze")
    assert analyze_res.status_code == 422
    assert "We couldn't identify any actionable requirements" in analyze_res.json()["detail"]

    # Verify assessment in DB is marked ANALYSIS_FAILED and not ANALYZED
    asm_db = db_session.query(Assessment).filter_by(id=asm_id).first()
    assert asm_db.status == "ANALYSIS_FAILED"
    assert asm_db.status != "ANALYZED"

def test_corrupted_pdf_upload_rejected(client):
    """3. Upload garbage bytes as PDF, verify 415 or 422 with clear message"""
    res = client.post("/api/assessments", json={"grant_name": "G", "application_name": "A"})
    asm_id = res.json()["id"]

    corrupted_bytes = b"%PDF-1.4\n%corrupted-byte-stream-not-a-valid-pdf\n%%EOF"
    upload_res = client.post(
        f"/api/assessments/{asm_id}/documents/upload",
        data={"doc_type": "guideline"},
        files={"file": ("corrupted.pdf", io.BytesIO(corrupted_bytes), "application/pdf")}
    )
    assert upload_res.status_code in (415, 422)

def test_image_only_pdf_rejected():
    """4. Upload PDF with empty/image pages, verify DocumentProcessingError"""
    doc = fitz.open()
    doc.new_page()  # Blank page without text
    pdf_bytes = doc.tobytes()
    doc.close()

    with pytest.raises(DocumentProcessingError) as exc_info:
        DocumentParser.parse(pdf_bytes, "scanned_or_image_only.pdf")

    assert "contains no extractable text" in str(exc_info.value)
    assert "We couldn't extract readable text from the guideline" in str(exc_info.value)

def test_persistence_matches_extracted_count(client, db_session):
    """5. Verify db.query(Requirement).count() == len(pipeline_res.requirements)"""
    res = client.post("/api/assessments", json={"grant_name": "CleanTech", "application_name": "EcoFilter"})
    asm_id = res.json()["id"]

    for doc_type, name in [("guideline", "sample_guideline.md"), ("application", "sample_application.md")]:
        with open(os.path.join(SAMPLES_DIR, name), "rb") as f:
            content = f.read()
        client.post(
            f"/api/assessments/{asm_id}/documents/upload",
            data={"doc_type": doc_type},
            files={"file": (name, io.BytesIO(content), "text/plain")}
        )

    analyze_res = client.post(f"/api/assessments/{asm_id}/analyze")
    assert analyze_res.status_code == 200
    data = analyze_res.json()

    persisted_count = db_session.query(Requirement).filter_by(assessment_id=asm_id).count()
    assert persisted_count == len(data["requirements"])
    assert persisted_count > 0

def test_mapping_coverage(client):
    """6. Verify every requirement has a corresponding mapping (no orphan requirements)"""
    res = client.post("/api/assessments", json={"grant_name": "CleanTech", "application_name": "EcoFilter"})
    asm_id = res.json()["id"]

    for doc_type, name in [("guideline", "sample_guideline.md"), ("application", "sample_application.md")]:
        with open(os.path.join(SAMPLES_DIR, name), "rb") as f:
            content = f.read()
        client.post(
            f"/api/assessments/{asm_id}/documents/upload",
            data={"doc_type": doc_type},
            files={"file": (name, io.BytesIO(content), "text/plain")}
        )

    analyze_res = client.post(f"/api/assessments/{asm_id}/analyze")
    assert analyze_res.status_code == 200
    data = analyze_res.json()

    requirements = data["requirements"]
    assert len(requirements) > 0
    for req in requirements:
        assert req["ai_status"] in ("SUPPORTED", "WEAK", "MISSING", "AMBIGUOUS")
        assert req["confidence"] is not None
        assert req["reasoning"] is not None

def test_deterministic_score_calculation(client):
    """7. Verify score = (completed mandatory / total mandatory) * 100"""
    res = client.post("/api/assessments", json={"grant_name": "CleanTech", "application_name": "EcoFilter"})
    asm_id = res.json()["id"]

    for doc_type, name in [("guideline", "sample_guideline.md"), ("application", "sample_application.md")]:
        with open(os.path.join(SAMPLES_DIR, name), "rb") as f:
            content = f.read()
        client.post(
            f"/api/assessments/{asm_id}/documents/upload",
            data={"doc_type": doc_type},
            files={"file": (name, io.BytesIO(content), "text/plain")}
        )

    analyze_res = client.post(f"/api/assessments/{asm_id}/analyze")
    assert analyze_res.status_code == 200
    score = analyze_res.json()["score"]

    if score["total_mandatory"] > 0:
        expected_percentage = round((score["mandatory_completed"] / score["total_mandatory"]) * 100.0, 1)
        assert score["completion_percentage"] == expected_percentage
    else:
        assert score["completion_percentage"] == 0.0

def test_structured_log_emission(client, caplog):
    """8. Verify key log events are emitted during pipeline execution (use caplog)"""
    import logging
    caplog.set_level(logging.INFO)

    res = client.post("/api/assessments", json={"grant_name": "CleanTech", "application_name": "EcoFilter"})
    asm_id = res.json()["id"]

    for doc_type, name in [("guideline", "sample_guideline.md"), ("application", "sample_application.md")]:
        with open(os.path.join(SAMPLES_DIR, name), "rb") as f:
            content = f.read()
        client.post(
            f"/api/assessments/{asm_id}/documents/upload",
            data={"doc_type": doc_type},
            files={"file": (name, io.BytesIO(content), "text/plain")}
        )

    analyze_res = client.post(f"/api/assessments/{asm_id}/analyze")
    assert analyze_res.status_code == 200

    log_messages = [record.getMessage() for record in caplog.records]
    assert any("document_uploaded" in msg for msg in log_messages)
    assert any("document_parsed" in msg for msg in log_messages)
    assert any("text_extracted" in msg for msg in log_messages)
    assert any("requirement_extraction_started" in msg for msg in log_messages)
    assert any("requirement_extraction_completed" in msg for msg in log_messages)
    assert any("mapping_started" in msg for msg in log_messages)
    assert any("mapping_completed" in msg for msg in log_messages)
    assert any("completeness_calculated" in msg for msg in log_messages)
    assert any("analysis_completed" in msg for msg in log_messages)
