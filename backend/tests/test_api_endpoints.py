import io
import pytest
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
