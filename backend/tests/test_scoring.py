import pytest
from app.models.requirement import Requirement
from app.models.mapping import RequirementMapping
from app.services.scoring_service import ScoringService

STATUSES = ["SUPPORTED", "WEAK", "MISSING", "AMBIGUOUS"]


def make_requirement(status, decision="PENDING", override_status=None, mandatory=True):
    requirement_id = f"{status}-{decision}-{override_status}-{mandatory}"
    requirement = Requirement(
        id=requirement_id,
        req_id_code=requirement_id,
        text="Requirement text",
        type="mandatory" if mandatory else "recommendation",
        mandatory=mandatory,
        category="eligibility",
        source_document="guideline",
        source_excerpt="Excerpt",
    )
    requirement.mapping = RequirementMapping(
        requirement_id=requirement_id,
        ai_status=status,
        reviewer_decision=decision,
        reviewer_override_status=override_status,
    )
    return requirement

def test_deterministic_scoring_all_supported():
    r1 = Requirement(id="r1", req_id_code="REQ-1", text="Text 1", type="mandatory", mandatory=True, category="eligibility", source_document="guideline", source_excerpt="Excerpt 1")
    r1.mapping = RequirementMapping(requirement_id="r1", ai_status="SUPPORTED", reviewer_decision="PENDING")

    r2 = Requirement(id="r2", req_id_code="REQ-2", text="Text 2", type="mandatory", mandatory=True, category="financial", source_document="guideline", source_excerpt="Excerpt 2")
    r2.mapping = RequirementMapping(requirement_id="r2", ai_status="SUPPORTED", reviewer_decision="PENDING")

    score = ScoringService.calculate_score([r1, r2])
    assert score.total_mandatory == 2
    assert score.mandatory_completed == 2
    assert score.completion_percentage == 100.0

@pytest.mark.parametrize(
    ("status", "completed", "weak", "missing", "ambiguous"),
    [
        ("SUPPORTED", 1, 0, 0, 0),
        ("WEAK", 0, 1, 0, 0),
        ("MISSING", 0, 0, 1, 0),
        ("AMBIGUOUS", 0, 0, 0, 1),
    ],
)
def test_each_ai_status_maps_to_deterministic_completion(
    status, completed, weak, missing, ambiguous
):
    score = ScoringService.calculate_score([make_requirement(status)])

    assert score.total_mandatory == 1
    assert score.completed == score.mandatory_completed == completed
    assert score.incomplete == 1 - completed
    assert score.mandatory_weak == weak
    assert score.mandatory_missing == missing
    assert score.mandatory_ambiguous == ambiguous
    assert score.completion_percentage == completed * 100.0


@pytest.mark.parametrize("ai_status", STATUSES)
@pytest.mark.parametrize(
    ("decision", "override_status", "expected_status"),
    [
        ("CONFIRMED", None, "SUPPORTED"),
        ("REJECTED", None, "MISSING"),
        ("CORRECTED", "SUPPORTED", "SUPPORTED"),
        ("CORRECTED", "WEAK", "WEAK"),
        ("CORRECTED", "MISSING", "MISSING"),
        ("CORRECTED", "AMBIGUOUS", "AMBIGUOUS"),
    ],
)
@pytest.mark.parametrize("mandatory", [True, False])
def test_reviewer_decisions_override_every_ai_status(
    ai_status, decision, override_status, expected_status, mandatory
):
    requirement = make_requirement(ai_status, decision, override_status, mandatory)
    score = ScoringService.calculate_score([requirement])
    is_complete = expected_status == "SUPPORTED"

    assert requirement.mapping.effective_status == expected_status
    if mandatory:
        assert score.completed == int(is_complete)
        assert score.incomplete == int(not is_complete)
        assert score.completion_percentage == (100.0 if is_complete else 0.0)
        assert score.recommendations_addressed == 0
    else:
        assert score.completed == 0
        assert score.incomplete == 0
        assert score.completion_percentage == 0.0
        assert score.recommendations_total == 1
        assert score.recommendations_addressed == int(is_complete)

def test_recommendations_do_not_reduce_mandatory_completion():
    requirements = [
        make_requirement("SUPPORTED"),
        make_requirement("SUPPORTED", mandatory=False),
        make_requirement("MISSING", mandatory=False),
        make_requirement("WEAK", mandatory=False),
        make_requirement("AMBIGUOUS", mandatory=False),
    ]

    score = ScoringService.calculate_score(requirements)
    assert score.total_mandatory == 1
    assert score.recommendations_total == 4
    assert score.recommendations_addressed == 1
    assert score.mandatory_completed == 1
    assert score.incomplete == 0
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
    assert score.total_mandatory == 0
    assert score.completed == 0
    assert score.incomplete == 0
    assert score.completion_percentage == 0.0


def test_zero_mandatory_requirements_keeps_recommendations_separate():
    score = ScoringService.calculate_score(
        [make_requirement("SUPPORTED", mandatory=False), make_requirement("MISSING", mandatory=False)]
    )

    assert score.total_mandatory == 0
    assert score.completed == 0
    assert score.incomplete == 0
    assert score.completion_percentage == 0.0
    assert score.recommendations_total == 2
    assert score.recommendations_addressed == 1


def test_completion_percentage_rounds_to_one_decimal_place():
    requirements = [make_requirement("SUPPORTED"), make_requirement("SUPPORTED"), make_requirement("WEAK")]

    score = ScoringService.calculate_score(requirements)

    assert score.completion_percentage == 66.7
