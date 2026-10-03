from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy.orm import Session
from app.database import get_db
from app.config import settings
from app.models.assessment import Assessment
from app.models.document import DocumentVersion
from app.schemas.assessment import ReviewedSummaryReportOut, SupportingDocOut
from app.schemas.ai import UnsupportedClaimItem, ClarificationQuestionItem
from app.services.scoring_service import ScoringService

router = APIRouter(prefix="/assessments/{assessment_id}/summary", tags=["Summary"])

@router.get("", response_model=ReviewedSummaryReportOut)
def get_summary_report(
    assessment_id: str = Path(..., description="Assessment UUID"),
    db: Session = Depends(get_db),
):
    assessment = db.query(Assessment).filter(Assessment.id == assessment_id).first()
    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")

    # Get active documents
    g_doc = (
        db.query(DocumentVersion)
        .filter(DocumentVersion.assessment_id == assessment_id, DocumentVersion.doc_type == "guideline", DocumentVersion.is_active == True)
        .first()
    )
    a_doc = (
        db.query(DocumentVersion)
        .filter(DocumentVersion.assessment_id == assessment_id, DocumentVersion.doc_type == "application", DocumentVersion.is_active == True)
        .first()
    )

    requirements = assessment.requirements
    supporting = assessment.supporting_documents
    score = ScoringService.calculate_score(requirements, supporting)

    # Reviewer decision breakdown
    decision_counts = {"CONFIRMED": 0, "CORRECTED": 0, "REJECTED": 0, "PENDING": 0}
    for r in requirements:
        if r.mapping:
            dec = r.mapping.reviewer_decision
            decision_counts[dec] = decision_counts.get(dec, 0) + 1
        else:
            decision_counts["PENDING"] += 1

    missing_docs = [
        SupportingDocOut(
            id=d.id,
            name=d.name,
            is_required=d.is_required,
            is_supplied=d.is_supplied,
            filename=d.filename,
            reviewer_notes=d.reviewer_notes,
        )
        for d in supporting
        if d.is_required and not d.is_supplied
    ]

    claims = [
        UnsupportedClaimItem(
            claim=c.claim,
            source_page=c.source_page,
            reason=c.reason,
            related_requirement=c.related_requirement,
            status=c.status,
        )
        for c in assessment.unsupported_claims
    ]

    questions = [
        ClarificationQuestionItem(
            requirement_id=q.requirement_id,
            question=q.question,
            gap_type=q.gap_type,
            suggested_evidence=q.suggested_evidence,
        )
        for q in assessment.clarification_questions
    ]

    return ReviewedSummaryReportOut(
        assessment_id=assessment.id,
        grant_name=assessment.grant_name,
        application_name=assessment.application_name,
        guideline_version=g_doc.version_number if g_doc else 1,
        application_version=a_doc.version_number if a_doc else 1,
        guideline_hash=g_doc.file_hash if g_doc else "N/A",
        application_hash=a_doc.file_hash if a_doc else "N/A",
        is_stale=assessment.is_stale,
        stale_reason=assessment.stale_reason,
        score=score,
        unsupported_claims=claims,
        missing_documents=missing_docs,
        clarification_questions=questions,
        reviewer_decisions_summary=decision_counts,
        raw_ai_audit_snapshot=assessment.raw_analysis_payload,
        disclaimer=settings.REGULATORY_DISCLAIMER,
    )
