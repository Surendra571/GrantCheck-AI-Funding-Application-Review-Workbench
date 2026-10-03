from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.assessment import Assessment
from app.models.requirement import Requirement
from app.models.mapping import RequirementMapping
from app.schemas.review import ReviewSubmissionRequest, ReviewSubmissionResponse
from app.services.scoring_service import ScoringService

router = APIRouter(prefix="/assessments/{assessment_id}/requirements", tags=["Reviews"])

@router.post("/{requirement_id}/review", response_model=ReviewSubmissionResponse)
def submit_requirement_review(
    assessment_id: str = Path(..., description="Assessment UUID"),
    requirement_id: str = Path(..., description="Requirement UUID or Code"),
    review_in: ReviewSubmissionRequest = ...,
    db: Session = Depends(get_db),
):
    assessment = db.query(Assessment).filter(Assessment.id == assessment_id).first()
    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")

    # Match by requirement id (UUID) or req_id_code
    requirement = (
        db.query(Requirement)
        .filter(
            Requirement.assessment_id == assessment_id,
            (Requirement.id == requirement_id) | (Requirement.req_id_code == requirement_id)
        )
        .first()
    )
    if not requirement:
        raise HTTPException(status_code=404, detail=f"Requirement '{requirement_id}' not found")

    mapping = requirement.mapping
    if not mapping:
        # Create a mapping record if none exists yet
        mapping = RequirementMapping(
            requirement_id=requirement.id,
            ai_status="MISSING",
            confidence=1.0,
            reasoning="Initialized by reviewer action"
        )
        db.add(mapping)
        db.flush()

    # Capture timestamp for reviewer action
    now = datetime.now(timezone.utc)
    mapping.reviewed_at = now
    mapping.reviewer_decision = review_in.decision

    if review_in.decision == "CONFIRMED":
        # Accept the AI mapping and confirm compliance
        mapping.reviewer_override_status = None
        if review_in.reviewer_notes:
            mapping.reviewer_notes = review_in.reviewer_notes.strip()

    elif review_in.decision == "CORRECTED":
        # Allow reviewer to change status and optionally edit evidence/citation
        mapping.reviewer_override_status = review_in.override_status
        mapping.reviewer_notes = review_in.reviewer_notes.strip()
        if review_in.override_evidence is not None:
            mapping.reviewer_evidence = review_in.override_evidence.strip()
        if review_in.override_citation is not None:
            mapping.reviewer_citation = review_in.override_citation.strip()

    elif review_in.decision == "REJECTED":
        # Mark mapping rejected with required reviewer note
        mapping.reviewer_override_status = None
        mapping.reviewer_notes = review_in.reviewer_notes.strip()

    db.commit()
    db.refresh(mapping)
    db.refresh(requirement)

    # Recalculate deterministic score using the updated human-reviewed state
    all_requirements = db.query(Requirement).filter(Requirement.assessment_id == assessment_id).all()
    all_supporting = assessment.supporting_documents
    recalculated_score = ScoringService.calculate_score(all_requirements, all_supporting)

    return ReviewSubmissionResponse(
        mapping_id=mapping.id,
        requirement_id=requirement.id,
        ai_status=mapping.ai_status,
        reviewer_decision=mapping.reviewer_decision,
        reviewer_override_status=mapping.reviewer_override_status,
        effective_status=mapping.effective_status,
        reviewer_notes=mapping.reviewer_notes,
        reviewed_at=mapping.reviewed_at,
        recalculated_score=recalculated_score,
        message=f"Requirement '{requirement.req_id_code}' review successfully recorded as {mapping.reviewer_decision}."
    )
