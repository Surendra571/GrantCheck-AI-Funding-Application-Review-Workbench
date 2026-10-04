import io
import pytest

def test_full_end_to_end_workflow(client):
    # 1. Create Assessment
    create_res = client.post("/api/assessments", json={
        "grant_name": "Horizon CleanTech Grant",
        "application_name": "EcoFilter Membrane Proposal"
    })
    assert create_res.status_code == 201
    asm_id = create_res.json()["id"]

    # 2. Upload Guideline Document
    guideline_text = (
        "# Horizon CleanTech Grant Guidelines\n\n"
        "## 1. Eligibility Criteria\n"
        "The lead applicant must be a UK-registered SME operating for at least 12 months.\n\n"
        "## 2. Financial Documentation\n"
        "Applications must include audited financial statements for the previous two financial years.\n\n"
        "## 3. Technical & Environmental Impact\n"
        "Projects must achieve a minimum 40% reduction in carbon emissions verified by life-cycle analysis.\n\n"
        "## 4. Commercial Partner Validation\n"
        "Applicants should provide letters of support from at least two commercial pilot partners.\n\n"
        "## 5. Risk Assessment & Governance\n"
        "A full risk assessment matrix identifying at least five technological and market risks with mitigation protocols must be included in Section D of the proposal narrative."
    )
    g_res = client.post(
        f"/api/assessments/{asm_id}/documents/upload",
        data={"doc_type": "guideline"},
        files={"file": ("guideline.txt", io.BytesIO(guideline_text.encode("utf-8")), "text/plain")}
    )
    assert g_res.status_code == 200
    assert g_res.json()["version_number"] == 1

    # 3. Upload Draft Application Document
    app_text = (
        "# EcoFilter Application Draft\n\n"
        "EcoFilter Ltd is a UK-registered micro-SME (Companies House #09876543) incorporated in March 2023.\n\n"
        "Two letters of support are attached from regional water utilities."
    )
    a_res = client.post(
        f"/api/assessments/{asm_id}/documents/upload",
        data={"doc_type": "application"},
        files={"file": ("application.txt", io.BytesIO(app_text.encode("utf-8")), "text/plain")}
    )
    assert a_res.status_code == 200
    assert a_res.json()["version_number"] == 1

    # 4. Analyze Application (Run 8-step controlled pipeline)
    analyze_res = client.post(f"/api/assessments/{asm_id}/analyze")
    assert analyze_res.status_code == 200
    asm_data = analyze_res.json()
    assert asm_data["status"] == "ANALYZED"
    assert asm_data["is_stale"] is False
    assert len(asm_data["requirements"]) == 5

    # Check raw analysis payload is persisted
    assert asm_data["raw_analysis_payload"] is not None
    assert "extracted_requirements" in asm_data["raw_analysis_payload"]

    # 5. Human Review Workflow: Confirm, Correct, and Reject
    reqs = asm_data["requirements"]
    r_supported = next(r for r in reqs if r["req_id_code"] == "REQ-001")
    r_missing = next(r for r in reqs if r["req_id_code"] == "REQ-002")
    r_rejected = next(r for r in reqs if r["req_id_code"] == "REQ-003")

    # 5a. Human confirms r_supported
    rev_res1 = client.post(
        f"/api/assessments/{asm_id}/requirements/{r_supported['id']}/review",
        json={"decision": "CONFIRMED", "reviewer_notes": "Verified Companies House filing."}
    )
    assert rev_res1.status_code == 200
    assert rev_res1.json()["reviewer_decision"] == "CONFIRMED"
    assert rev_res1.json()["effective_status"] == "SUPPORTED"

    # 5b. Human corrects r_missing to SUPPORTED after viewing supplementary offline audit
    rev_res2 = client.post(
        f"/api/assessments/{asm_id}/requirements/{r_missing['id']}/review",
        json={
            "decision": "CORRECTED",
            "override_status": "SUPPORTED",
            "reviewer_notes": "Reviewed audited financial statement delivered via secure portal.",
            "override_evidence": "Signed EY Auditor Report dated 15 Jan 2025"
        }
    )
    assert rev_res2.status_code == 200
    assert rev_res2.json()["reviewer_decision"] == "CORRECTED"
    assert rev_res2.json()["effective_status"] == "SUPPORTED"

    # 5c. Human rejects a mapping the verifier cannot support with a valid citation
    rev_res3 = client.post(
        f"/api/assessments/{asm_id}/requirements/{r_rejected['id']}/review",
        json={"decision": "REJECTED", "reviewer_notes": "No verifiable LCA evidence was provided."}
    )
    assert rev_res3.status_code == 200
    assert rev_res3.json()["reviewer_decision"] == "REJECTED"
    assert rev_res3.json()["effective_status"] == "MISSING"

    # 6. Verify Reviewed Summary Report uses the human reviewed state
    summary_res = client.get(f"/api/assessments/{asm_id}/summary")
    assert summary_res.status_code == 200
    sum_data = summary_res.json()
    assert sum_data["score"]["total_mandatory"] == 4
    assert sum_data["score"]["completed"] == 2
    assert sum_data["score"]["incomplete"] == 2
    assert sum_data["score"]["completion_percentage"] == 50.0
    assert sum_data["score"]["recommendations_total"] == 1
    assert sum_data["score"]["recommendations_addressed"] == 0
    assert sum_data["score"]["confirmed_count"] == 1
    assert sum_data["score"]["corrected_count"] == 1
    assert sum_data["score"]["rejected_count"] == 1
    assert sum_data["reviewer_decisions_summary"]["CONFIRMED"] == 1
    assert sum_data["reviewer_decisions_summary"]["CORRECTED"] == 1
    assert sum_data["reviewer_decisions_summary"]["REJECTED"] == 1
    assert sum_data["is_stale"] is False

    # 7. Document Replacement -> Version Increment & Stale Detection
    updated_guideline = guideline_text + "\n\n## 4. Mandatory Security Clearance Requirement"
    g_res2 = client.post(
        f"/api/assessments/{asm_id}/documents/upload",
        data={"doc_type": "guideline"},
        files={"file": ("guideline_v2.txt", io.BytesIO(updated_guideline.encode("utf-8")), "text/plain")}
    )
    assert g_res2.status_code == 200
    assert g_res2.json()["version_number"] == 2

    # Assessment must now be marked STALE
    asm_after_update = client.get(f"/api/assessments/{asm_id}").json()
    assert asm_after_update["is_stale"] is True
    assert "Assessment stale — source document changed" in asm_after_update["stale_reason"]

    # 8. Re-analyze against the updated guideline in a new auditable run
    reanalyze_res = client.post(f"/api/assessments/{asm_id}/reanalyze")
    assert reanalyze_res.status_code == 200
    reanalyzed = reanalyze_res.json()
    assert reanalyzed["id"] != asm_id
    assert reanalyzed["parent_assessment_id"] == asm_id
    assert reanalyzed["run_number"] == 2
    assert reanalyzed["status"] == "ANALYZED"
    assert reanalyzed["is_stale"] is False
    assert reanalyzed["guideline_version"] == 2
    assert reanalyzed["score"]["completion_percentage"] == 25.0

    original_after_reanalysis = client.get(f"/api/assessments/{asm_id}").json()
    assert original_after_reanalysis["is_stale"] is True
