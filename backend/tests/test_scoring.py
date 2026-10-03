import pytest
from app.models.requirement import Requirement
from app.models.mapping import RequirementMapping
from app.models.supporting_doc import SupportingDocument
from app.services.scoring_service import ScoringService

def test_deterministic_scoring_all_supported():
    r1 = Requirement(id="r1", req_id_code="REQ-1", text="Text 1", type="mandatory", mandatory=True, category="eligibility", source_document="guideline", source_excerpt="Excerpt 1")
    r1.mapping = RequirementMapping(requirement_id="r1", ai_status="SUPPORTED", reviewer_decision="PENDING")

    r2 = Requirement(id="r2", req_id_code="REQ-2", text="Text 2", type="mandatory", mandatory=True, category="financial", source_document="guideline", source_excerpt="Excerpt 2")
    r2.mapping = RequirementMapping(requirement_id="r2", ai_status="SUPPORTED", reviewer_decision="PENDING")

    score = ScoringService.calculate_score([r1, r2])
    assert score.total_mandatory == 2
    assert score.mandatory_completed == 2
    assert score.completion_percentage == 100.0

def test_deterministic_scoring_weak_and_missing_are_incomplete():
    r1 = Requirement(id="r1", req_id_code="REQ-1", text="Text 1", type="mandatory", mandatory=True, category="eligibility", source_document="guideline", source_excerpt="Excerpt 1")
    r1.mapping = RequirementMapping(requirement_id="r1", ai_status="SUPPORTED", reviewer_decision="PENDING")

    r2 = Requirement(id="r2", req_id_code="REQ-2", text="Text 2", type="mandatory", mandatory=True, category="financial", source_document="guideline", source_excerpt="Excerpt 2")
    r2.mapping = RequirementMapping(requirement_id="r2", ai_status="WEAK", reviewer_decision="PENDING")

    r3 = Requirement(id="r3", req_id_code="REQ-3", text="Text 3", type="mandatory", mandatory=True, category="project", source_document="guideline", source_excerpt="Excerpt 3")
    r3.mapping = RequirementMapping(requirement_id="r3", ai_status="MISSING", reviewer_decision="PENDING")

    score = ScoringService.calculate_score([r1, r2, r3])
    assert score.total_mandatory == 3
    assert score.mandatory_completed == 1
    assert score.mandatory_weak == 1
    assert score.mandatory_missing == 1
    assert score.completion_percentage == round(1 / 3 * 100, 2)

def test_recommendations_do_not_reduce_mandatory_completion():
    r1 = Requirement(id="r1", req_id_code="REQ-1", text="Mandatory 1", type="mandatory", mandatory=True, category="eligibility", source_document="guideline", source_excerpt="E1")
    r1.mapping = RequirementMapping(requirement_id="r1", ai_status="SUPPORTED", reviewer_decision="PENDING")

    # Recommendation with missing status
    r2 = Requirement(id="r2", req_id_code="REQ-2", text="Rec 1", type="recommendation", mandatory=False, category="recommendation", source_document="guideline", source_excerpt="E2")
    r2.mapping = RequirementMapping(requirement_id="r2", ai_status="MISSING", reviewer_decision="PENDING")

    score = ScoringService.calculate_score([r1, r2])
    assert score.total_mandatory == 1
    assert score.total_recommendations == 1
    assert score.mandatory_completed == 1
    assert score.completion_percentage == 100.0  # Recommendation does not reduce mandatory score

def test_reviewer_rejection_overrides_to_incomplete():
    """Example from prompt: AI: SUPPORTED, Reviewer: REJECTED, Final: Incomplete"""
    r1 = Requirement(id="r1", req_id_code="REQ-1", text="Text 1", type="mandatory", mandatory=True, category="eligibility", source_document="guideline", source_excerpt="E1")
    r1.mapping = RequirementMapping(
        requirement_id="r1",
        ai_status="SUPPORTED",
        reviewer_decision="REJECTED",
        reviewer_notes="Evidence is from an uncertified partner."
    )

    score = ScoringService.calculate_score([r1])
    assert r1.mapping.effective_status == "MISSING"
    assert not r1.mapping.is_final_complete
    assert score.mandatory_completed == 0
    assert score.rejected_count == 1
    assert score.completion_percentage == 0.0

def test_reviewer_confirmation_overrides_to_complete():
    """Example from prompt: AI: MISSING, Reviewer: CONFIRMED, Final: Complete"""
    r1 = Requirement(id="r1", req_id_code="REQ-1", text="Text 1", type="mandatory", mandatory=True, category="eligibility", source_document="guideline", source_excerpt="E1")
    r1.mapping = RequirementMapping(
        requirement_id="r1",
        ai_status="MISSING",
        reviewer_decision="CONFIRMED",
        reviewer_notes="Confirmed via separate registration certificate."
    )

    score = ScoringService.calculate_score([r1])
    assert r1.mapping.effective_status == "SUPPORTED"
    assert r1.mapping.is_final_complete
    assert score.mandatory_completed == 1
    assert score.confirmed_count == 1
    assert score.completion_percentage == 100.0

def test_reviewer_correction_overrides_status():
    r1 = Requirement(id="r1", req_id_code="REQ-1", text="Text 1", type="mandatory", mandatory=True, category="eligibility", source_document="guideline", source_excerpt="E1")
    r1.mapping = RequirementMapping(
        requirement_id="r1",
        ai_status="WEAK",
        reviewer_decision="CORRECTED",
        reviewer_override_status="SUPPORTED",
        reviewer_notes="Verified ISO 14040 report attached in Appendix C."
    )

    score = ScoringService.calculate_score([r1])
    assert r1.mapping.effective_status == "SUPPORTED"
    assert score.mandatory_completed == 1
    assert score.corrected_count == 1
    assert score.completion_percentage == 100.0

def test_empty_requirements_edge_case():
    score = ScoringService.calculate_score([])
    assert score.total_requirements == 0
    assert score.completion_percentage == 0.0
