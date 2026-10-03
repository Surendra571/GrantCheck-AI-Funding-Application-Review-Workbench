import pytest
from pydantic import ValidationError
from app.schemas.ai import (
    RequirementExtracted,
    RequirementMappingItem,
    UnsupportedClaimItem,
    ClarificationQuestionItem,
)
from app.schemas.review import ReviewSubmissionRequest

def test_valid_requirement_extracted():
    req = RequirementExtracted(
        id="REQ-1",
        text="Applicant must be registered in the UK.",
        type="mandatory",
        mandatory=True,
        category="eligibility",
        source_document="guideline",
        source_page=1,
        source_section="1. Eligibility",
        source_excerpt="Applicant must be registered in the UK."
    )
    assert req.id == "REQ-1"
    assert req.mandatory is True

def test_invalid_requirement_category_fails():
    with pytest.raises(ValidationError):
        RequirementExtracted(
            id="REQ-1",
            text="Text",
            type="mandatory",
            mandatory=True,
            category="invalid_category",  # Not in allowed categories
            source_document="guideline",
            source_excerpt="Text"
        )

def test_valid_mapping_item():
    m = RequirementMappingItem(
        requirement_id="REQ-1",
        status="SUPPORTED",
        evidence="Evidence found.",
        source_document="application",
        source_page=1,
        source_section="Profile",
        confidence=0.9,
        reasoning="Sufficient evidence provided."
    )
    assert m.status == "SUPPORTED"

def test_invalid_mapping_status_fails():
    with pytest.raises(ValidationError):
        RequirementMappingItem(
            requirement_id="REQ-1",
            status="UNKNOWN_STATUS",  # Not in SUPPORTED, WEAK, MISSING, AMBIGUOUS
            evidence=None,
            source_document="application",
            confidence=0.5,
            reasoning="Reason"
        )

def test_unsupported_claim_schema():
    c = UnsupportedClaimItem(
        claim="We are the sole provider globally.",
        source_page=2,
        reason="No market study provided.",
        related_requirement="REQ-2"
    )
    assert "No supporting evidence found in supplied materials" in c.status

def test_clarification_question_schema():
    q = ClarificationQuestionItem(
        requirement_id="REQ-3",
        question="Please provide audited accounts.",
        gap_type="MISSING",
        suggested_evidence="Audited accounts."
    )
    assert q.gap_type == "MISSING"

def test_review_submission_request_validation():
    # Confirm doesn't strictly need notes
    r_confirm = ReviewSubmissionRequest(decision="CONFIRMED")
    assert r_confirm.decision == "CONFIRMED"

    # Correct requires notes and override_status
    with pytest.raises(ValueError, match="Reviewer notes are mandatory"):
        ReviewSubmissionRequest(decision="CORRECTED", override_status="SUPPORTED")

    with pytest.raises(ValueError, match="override status must be specified"):
        ReviewSubmissionRequest(decision="CORRECTED", reviewer_notes="Explanation here")

    # Reject requires notes
    with pytest.raises(ValueError, match="Reviewer notes are mandatory"):
        ReviewSubmissionRequest(decision="REJECTED")
