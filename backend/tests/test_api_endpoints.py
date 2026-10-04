import io
from pathlib import Path
import pytest
from app.config import settings
from app.models.assessment import Assessment
from app.models.requirement import Requirement
from app.models.mapping import RequirementMapping

def test_health_check(client):
    res = client.get("/")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "online"
    assert "notice" in data

def test_create_and_get_assessment(client):
    res = client.post("/api/assessments", json={
        "title": "CleanTech Horizon Review",
        "grant_name": "Horizon CleanTech",
        "application_name": "EcoFilter Proposal"
    })
    assert res.status_code == 201
    data = res.json()
    assert data["grant_name"] == "Horizon CleanTech"
    asm_id = data["id"]

    get_res = client.get(f"/api/assessments/{asm_id}")
    assert get_res.status_code == 200
    assert get_res.json()["id"] == asm_id

def test_upload_documents(client):
    res = client.post("/api/assessments", json={
        "grant_name": "Grant",
        "application_name": "App"
    })
    asm_id = res.json()["id"]

    file_content = b"# Guidelines\nEligible applicants must be UK SMEs."
    upload_res = client.post(
        f"/api/assessments/{asm_id}/documents/upload",
        data={"doc_type": "guideline"},
        files={"file": ("guidelines.txt", io.BytesIO(file_content), "text/plain")}
    )
    assert upload_res.status_code == 200
    data = upload_res.json()
    assert data["version_number"] == 1
    assert data["filename"] == "guidelines.txt"

def test_upload_invalid_type_error(client):
    res = client.post("/api/assessments", json={"grant_name": "G", "application_name": "A"})
    asm_id = res.json()["id"]

    upload_res = client.post(
        f"/api/assessments/{asm_id}/documents/upload",
        data={"doc_type": "guideline"},
        files={"file": ("image.png", io.BytesIO(b"data"), "image/png")}
    )
    assert upload_res.status_code == 415

def test_upload_empty_file_error(client):
    res = client.post("/api/assessments", json={"grant_name": "G", "application_name": "A"})
    asm_id = res.json()["id"]

    upload_res = client.post(
        f"/api/assessments/{asm_id}/documents/upload",
        data={"doc_type": "guideline"},
        files={"file": ("empty.txt", io.BytesIO(b""), "text/plain")}
    )
    assert upload_res.status_code == 400


def test_upload_size_limit_is_enforced(client, monkeypatch):
    monkeypatch.setattr(settings, "MAX_UPLOAD_SIZE_MB", 1)
    assessment = client.post(
        "/api/assessments",
        json={"grant_name": "G", "application_name": "A"},
    ).json()

    response = client.post(
        f"/api/assessments/{assessment['id']}/documents/upload",
        data={"doc_type": "guideline"},
        files={"file": ("large.txt", io.BytesIO(b"x" * (1024 * 1024 + 1)), "text/plain")},
    )

    assert response.status_code == 413
    assert "limit" in response.json()["detail"]
    assert client.get(f"/api/assessments/{assessment['id']}/documents").json() == []


def test_upload_unknown_document_type_error(client):
    assessment = client.post(
        "/api/assessments",
        json={"grant_name": "G", "application_name": "A"},
    ).json()

    response = client.post(
        f"/api/assessments/{assessment['id']}/documents/upload",
        data={"doc_type": "budget"},
        files={"file": ("budget.txt", io.BytesIO(b"Budget text"), "text/plain")},
    )

    assert response.status_code == 400
    assert "Invalid doc_type" in response.json()["detail"]


def test_upload_to_unknown_assessment_returns_not_found(client):
    response = client.post(
        "/api/assessments/not-an-assessment/documents/upload",
        data={"doc_type": "guideline"},
        files={"file": ("guideline.txt", io.BytesIO(b"Guideline text"), "text/plain")},
    )

    assert response.status_code == 404


def test_upload_whitespace_document_returns_unsupported_media_type(client):
    assessment = client.post(
        "/api/assessments",
        json={"grant_name": "G", "application_name": "A"},
    ).json()

    response = client.post(
        f"/api/assessments/{assessment['id']}/documents/upload",
        data={"doc_type": "guideline"},
        files={"file": ("blank.txt", io.BytesIO(b" \r\n\t"), "text/plain")},
    )

    assert response.status_code == 415
    assert "is empty" in response.json()["detail"]
    assert client.get(f"/api/assessments/{assessment['id']}/documents").json() == []


def test_duplicate_document_upload_returns_conflict_without_new_version(client):
    assessment = client.post(
        "/api/assessments",
        json={"grant_name": "G", "application_name": "A"},
    ).json()
    upload_url = f"/api/assessments/{assessment['id']}/documents/upload"
    document_bytes = b"# Guideline\nApplicants must submit audited accounts."

    first_response = client.post(
        upload_url,
        data={"doc_type": "guideline"},
        files={"file": ("guideline.txt", io.BytesIO(document_bytes), "text/plain")},
    )
    duplicate_response = client.post(
        upload_url,
        data={"doc_type": "guideline"},
        files={"file": ("guideline-copy.txt", io.BytesIO(document_bytes), "text/plain")},
    )

    assert first_response.status_code == 200
    assert duplicate_response.status_code == 409
    documents = client.get(f"/api/assessments/{assessment['id']}/documents").json()
    assert len(documents) == 1
    assert documents[0]["version_number"] == 1


def test_analyze_requires_both_source_documents(client):
    assessment = client.post(
        "/api/assessments",
        json={"grant_name": "G", "application_name": "A"},
    ).json()

    response = client.post(f"/api/assessments/{assessment['id']}/analyze")

    assert response.status_code == 400
    assert "Both a Grant Guideline and Draft Application" in response.json()["detail"]


def test_reanalyze_requires_both_source_documents(client):
    assessment = client.post(
        "/api/assessments",
        json={"grant_name": "G", "application_name": "A"},
    ).json()

    response = client.post(f"/api/assessments/{assessment['id']}/reanalyze")

    assert response.status_code == 400
    assert "Both a Grant Guideline and Draft Application" in response.json()["detail"]


def test_rejected_review_without_required_notes_returns_422(client):
    response = client.post(
        "/api/assessments/not-an-assessment/requirements/not-a-requirement/review",
        json={"decision": "REJECTED"},
    )

    assert response.status_code == 422
    assert "Reviewer notes are mandatory" in response.json()["detail"][0]["msg"]


def test_analysis_commit_failure_rolls_back_generated_records(client, db_session, monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(tmp_path))
    assessment = client.post(
        "/api/assessments",
        json={"grant_name": "G", "application_name": "A"},
    ).json()
    samples = Path(__file__).parent.parent / "app" / "samples"
    for doc_type, filename in [
        ("guideline", "sample_guideline.md"),
        ("application", "sample_application.md"),
    ]:
        content = (samples / filename).read_bytes()
        upload = client.post(
            f"/api/assessments/{assessment['id']}/documents/upload",
            data={"doc_type": doc_type},
            files={"file": (filename, io.BytesIO(content), "text/plain")},
        )
        assert upload.status_code == 200

    real_commit = db_session.commit
    commit_count = 0

    def fail_final_analysis_commit():
        nonlocal commit_count
        commit_count += 1
        if commit_count == 2:
            raise RuntimeError("database-secret-sentinel")
        real_commit()

    monkeypatch.setattr(db_session, "commit", fail_final_analysis_commit)
    response = client.post(f"/api/assessments/{assessment['id']}/analyze")

    assert response.status_code == 500
    assert "database-secret-sentinel" not in response.text
    stored_assessment = db_session.query(Assessment).filter_by(id=assessment["id"]).one()
    assert stored_assessment.status == "ERROR"
    assert db_session.query(Requirement).filter_by(assessment_id=assessment["id"]).count() == 0

def test_supporting_documents_crud(client):
    res = client.post("/api/assessments", json={"grant_name": "G", "application_name": "A"})
    asm_id = res.json()["id"]

    # Create
    create_res = client.post(f"/api/assessments/{asm_id}/supporting-docs", json={
        "name": "Audited Accounts",
        "is_required": True,
        "is_supplied": False,
        "reviewer_notes": "Awaiting FY2024"
    })
    assert create_res.status_code == 201
    doc_id = create_res.json()["id"]

    # Patch / Update
    patch_res = client.patch(f"/api/assessments/{asm_id}/supporting-docs/{doc_id}", json={
        "is_supplied": True,
        "filename": "accounts_2024.pdf"
    })
    assert patch_res.status_code == 200
    assert patch_res.json()["is_supplied"] is True

    # Delete
    del_res = client.delete(f"/api/assessments/{asm_id}/supporting-docs/{doc_id}")
    assert del_res.status_code == 204

def test_review_confirm_recalculation(client, db_session):
    asm = Assessment(title="Test", grant_name="Grant", application_name="App", status="ANALYZED")
    db_session.add(asm)
    db_session.flush()

    r1 = Requirement(assessment_id=asm.id, req_id_code="REQ-001", text="Req 1", type="mandatory", mandatory=True, category="eligibility", source_document="g", source_excerpt="e")
    db_session.add(r1)
    db_session.flush()

    m1 = RequirementMapping(requirement_id=r1.id, ai_status="MISSING", reviewer_decision="PENDING")
    db_session.add(m1)
    db_session.commit()

    # Reviewer confirms: AI: MISSING, Reviewer: CONFIRMED -> Final: Complete (100%)
    res = client.post(
        f"/api/assessments/{asm.id}/requirements/{r1.id}/review",
        json={"decision": "CONFIRMED", "reviewer_notes": "Verified offline certificate"}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["ai_status"] == "MISSING"
    assert data["reviewer_decision"] == "CONFIRMED"
    assert data["effective_status"] == "SUPPORTED"
    assert data["reviewed_at"] is not None
    assert data["recalculated_score"]["completion_percentage"] == 100.0
    assert data["recalculated_score"]["confirmed_count"] == 1

def test_review_reject_recalculation(client, db_session):
    asm = Assessment(title="Test", grant_name="Grant", application_name="App", status="ANALYZED")
    db_session.add(asm)
    db_session.flush()

    r1 = Requirement(assessment_id=asm.id, req_id_code="REQ-001", text="Req 1", type="mandatory", mandatory=True, category="eligibility", source_document="g", source_excerpt="e")
    db_session.add(r1)
    db_session.flush()

    m1 = RequirementMapping(requirement_id=r1.id, ai_status="SUPPORTED", reviewer_decision="PENDING")
    db_session.add(m1)
    db_session.commit()

    # Reviewer rejects: AI: SUPPORTED, Reviewer: REJECTED -> Final: Incomplete (0%)
    res = client.post(
        f"/api/assessments/{asm.id}/requirements/{r1.id}/review",
        json={"decision": "REJECTED", "reviewer_notes": "Evidence citation is fabricated."}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["ai_status"] == "SUPPORTED"
    assert data["reviewer_decision"] == "REJECTED"
    assert data["effective_status"] == "MISSING"
    assert data["recalculated_score"]["completion_percentage"] == 0.0
    assert data["recalculated_score"]["rejected_count"] == 1

def test_review_correct_recalculation(client, db_session):
    asm = Assessment(title="Test", grant_name="Grant", application_name="App", status="ANALYZED")
    db_session.add(asm)
    db_session.flush()

    r1 = Requirement(assessment_id=asm.id, req_id_code="REQ-001", text="Req 1", type="mandatory", mandatory=True, category="eligibility", source_document="g", source_excerpt="e")
    db_session.add(r1)
    db_session.flush()

    m1 = RequirementMapping(requirement_id=r1.id, ai_status="WEAK", reviewer_decision="PENDING")
    db_session.add(m1)
    db_session.commit()

    # Reviewer corrects: AI: WEAK, Reviewer: CORRECTED to SUPPORTED -> Final: Complete (100%)
    res = client.post(
        f"/api/assessments/{asm.id}/requirements/{r1.id}/review",
        json={
            "decision": "CORRECTED",
            "override_status": "SUPPORTED",
            "reviewer_notes": "Reviewed supplementary annex with accredited LCA.",
            "override_evidence": "Full LCA ISO 14040 report attached in Annex B."
        }
    )
    assert res.status_code == 200
    data = res.json()
    assert data["ai_status"] == "WEAK"
    assert data["reviewer_decision"] == "CORRECTED"
    assert data["reviewer_override_status"] == "SUPPORTED"
    assert data["effective_status"] == "SUPPORTED"
    assert data["recalculated_score"]["completion_percentage"] == 100.0
    assert data["recalculated_score"]["corrected_count"] == 1
