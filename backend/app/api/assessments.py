import os
import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.assessment import Assessment
from app.models.document import DocumentVersion
from app.models.requirement import Requirement
from app.models.mapping import RequirementMapping
from app.models.supporting_doc import SupportingDocument
from app.models.unsupported_claim import UnsupportedClaim, ClarificationQuestion
from app.schemas.assessment import (
    AssessmentCreate,
    AssessmentListItem,
    AssessmentDetailOut,
    RequirementDetailOut,
    DocumentVersionOut,
    SupportingDocOut,
)
from app.services.llm_client import get_llm_client
from app.services.pipeline_orchestrator import PipelineOrchestrator
from app.services.scoring_service import ScoringService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/assessments", tags=["Assessments"])

def _build_detail_out(assessment: Assessment, db: Session) -> AssessmentDetailOut:
    g_doc = next((d for d in assessment.documents if d.doc_type == "guideline" and d.is_active), None)
    a_doc = next((d for d in assessment.documents if d.doc_type == "application" and d.is_active), None)

    req_outs: List[RequirementDetailOut] = []
    for r in assessment.requirements:
        m = r.mapping
        req_outs.append(
            RequirementDetailOut(
                id=r.id,
                req_id_code=r.req_id_code,
                text=r.text,
                type=r.type,
                mandatory=r.mandatory,
                category=r.category,
                source_document=r.source_document,
                source_page=r.source_page,
                source_section=r.source_section,
                source_excerpt=r.source_excerpt,
                mapping_id=m.id if m else None,
                ai_status=m.ai_status if m else None,
                evidence=m.evidence if m else None,
                evidence_source_doc=m.source_document if m else None,
                evidence_page=m.source_page if m else None,
                evidence_section=m.source_section if m else None,
                confidence=m.confidence if m else None,
                reasoning=m.reasoning if m else None,
                reviewer_decision=m.reviewer_decision if m else "PENDING",
                reviewer_override_status=m.reviewer_override_status if m else None,
                reviewer_notes=m.reviewer_notes if m else None,
                reviewer_evidence=m.reviewer_evidence if m else None,
                reviewer_citation=m.reviewer_citation if m else None,
                reviewed_at=m.reviewed_at if m else None,
                effective_status=m.effective_status if m else "MISSING",
                is_final_complete=m.is_final_complete if m else False,
            )
        )

    doc_outs = [
        DocumentVersionOut(
            id=d.id,
            doc_type=d.doc_type,
            filename=d.filename,
            file_hash=d.file_hash,
            version_number=d.version_number,
            is_active=d.is_active,
            page_count=d.page_count,
            upload_timestamp=d.upload_timestamp,
        )
        for d in assessment.documents
    ]

    sup_outs = [
        SupportingDocOut(
            id=s.id,
            name=s.name,
            is_required=s.is_required,
            is_supplied=s.is_supplied,
            filename=s.filename,
            reviewer_notes=s.reviewer_notes,
        )
        for s in assessment.supporting_documents
    ]

    score = ScoringService.calculate_score(assessment.requirements, assessment.supporting_documents)

    return AssessmentDetailOut(
        id=assessment.id,
        title=assessment.title,
        grant_name=assessment.grant_name,
        application_name=assessment.application_name,
        status=assessment.status,
        guideline_version=assessment.guideline_version,
        application_version=assessment.application_version,
        run_number=assessment.run_number,
        parent_assessment_id=assessment.parent_assessment_id,
        is_stale=assessment.is_stale,
        stale_reason=assessment.stale_reason,
        raw_analysis_payload=assessment.raw_analysis_payload,
        created_at=assessment.created_at,
        updated_at=assessment.updated_at,
        active_guideline=next((d for d in doc_outs if d.doc_type == "guideline" and d.is_active), None),
        active_application=next((d for d in doc_outs if d.doc_type == "application" and d.is_active), None),
        document_versions=doc_outs,
        score=score,
        requirements=req_outs,
        supporting_documents=sup_outs,
    )

@router.post("", response_model=AssessmentDetailOut, status_code=201)
def create_assessment(item: AssessmentCreate, db: Session = Depends(get_db)):
    title = item.title or f"{item.application_name} vs {item.grant_name}"
    assessment = Assessment(
        title=title,
        grant_name=item.grant_name,
        application_name=item.application_name,
        status="DRAFT",
        guideline_version=1,
        application_version=1,
        run_number=1,
        is_stale=False,
    )
    db.add(assessment)
    db.commit()
    db.refresh(assessment)
    return _build_detail_out(assessment, db)

@router.get("", response_model=List[AssessmentListItem])
def list_assessments(db: Session = Depends(get_db)):
    assessments = db.query(Assessment).order_by(Assessment.created_at.desc()).all()
    results = []
    for a in assessments:
        score = ScoringService.calculate_score(a.requirements, a.supporting_documents)
        results.append(
            AssessmentListItem(
                id=a.id,
                title=a.title,
                grant_name=a.grant_name,
                application_name=a.application_name,
                status=a.status,
                guideline_version=a.guideline_version,
                application_version=a.application_version,
                run_number=a.run_number,
                parent_assessment_id=a.parent_assessment_id,
                is_stale=a.is_stale,
                stale_reason=a.stale_reason,
                created_at=a.created_at,
                updated_at=a.updated_at,
                completion_percentage=score.completion_percentage,
            )
        )
    return results

@router.get("/{id}", response_model=AssessmentDetailOut)
def get_assessment(id: str = Path(..., description="Assessment UUID"), db: Session = Depends(get_db)):
    assessment = db.query(Assessment).filter(Assessment.id == id).first()
    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")
    return _build_detail_out(assessment, db)

@router.delete("/{id}", status_code=204)
def delete_assessment(id: str = Path(..., description="Assessment UUID"), db: Session = Depends(get_db)):
    assessment = db.query(Assessment).filter(Assessment.id == id).first()
    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")
    db.delete(assessment)
    db.commit()
    return None

def _execute_pipeline_for_assessment(assessment: Assessment, g_doc: DocumentVersion, a_doc: DocumentVersion, db: Session):
    if not os.path.exists(g_doc.storage_path) or not os.path.exists(a_doc.storage_path):
        raise HTTPException(status_code=500, detail="Source document files missing from storage disk.")

    with open(g_doc.storage_path, "rb") as f:
        g_bytes = f.read()
    with open(a_doc.storage_path, "rb") as f:
        a_bytes = f.read()

    assessment.status = "ANALYZING"
    db.commit()

    try:
        llm = get_llm_client()
        orchestrator = PipelineOrchestrator(llm)
        pipeline_res = orchestrator.run_pipeline(
            guideline_bytes=g_bytes,
            guideline_filename=g_doc.filename,
            application_bytes=a_bytes,
            application_filename=a_doc.filename,
        )

        # Clear existing analysis records for this specific assessment
        db.query(Requirement).filter(Requirement.assessment_id == assessment.id).delete()
        db.query(UnsupportedClaim).filter(UnsupportedClaim.assessment_id == assessment.id).delete()
        db.query(ClarificationQuestion).filter(ClarificationQuestion.assessment_id == assessment.id).delete()

        # Save requirements and mappings
        extracted_reqs = pipeline_res["requirements"]
        verified_mappings = pipeline_res["mappings"]
        map_by_id = {m.requirement_id: m for m in verified_mappings}

        for r_item in extracted_reqs:
            req_db = Requirement(
                assessment_id=assessment.id,
                req_id_code=r_item.id,
                text=r_item.text,
                type=r_item.type,
                mandatory=r_item.mandatory,
                category=r_item.category,
                source_document=r_item.source_document,
                source_page=r_item.source_page,
                source_section=r_item.source_section,
                source_excerpt=r_item.source_excerpt,
            )
            db.add(req_db)
            db.flush()

            m_item = map_by_id.get(r_item.id)
            if m_item:
                mapping_db = RequirementMapping(
                    requirement_id=req_db.id,
                    ai_status=m_item.status,
                    evidence=m_item.evidence,
                    source_document=m_item.source_document,
                    source_page=m_item.source_page,
                    source_section=m_item.source_section,
                    confidence=m_item.confidence,
                    reasoning=m_item.reasoning,
                    reviewer_decision="PENDING",
                )
                db.add(mapping_db)

        # Save unsupported claims
        for c in pipeline_res["unsupported_claims"]:
            claim_db = UnsupportedClaim(
                assessment_id=assessment.id,
                claim=c.claim,
                source_page=c.source_page,
                reason=c.reason,
                related_requirement=c.related_requirement,
                status=c.status,
            )
            db.add(claim_db)

        # Save clarification questions
        for q in pipeline_res["clarification_questions"]:
            q_db = ClarificationQuestion(
                assessment_id=assessment.id,
                requirement_id=q.requirement_id,
                question=q.question,
                gap_type=q.gap_type,
                suggested_evidence=q.suggested_evidence,
            )
            db.add(q_db)

        assessment.guideline_version = g_doc.version_number
        assessment.application_version = a_doc.version_number
        assessment.raw_analysis_payload = pipeline_res["audit_snapshot"]
        assessment.status = "ANALYZED"
        assessment.is_stale = False
        assessment.stale_reason = None
        db.commit()
        db.refresh(assessment)

    except Exception as e:
        db.rollback()
        assessment.status = "ERROR"
        db.commit()
        logger.error(
            "Pipeline analysis failed for assessment %s (%s)",
            assessment.id,
            type(e).__name__,
        )
        raise HTTPException(
            status_code=500,
            detail="Pipeline analysis execution failed. Check server logs for the failure type.",
        ) from None

@router.post("/{id}/analyze", response_model=AssessmentDetailOut)
def analyze_assessment(id: str = Path(..., description="Assessment UUID"), db: Session = Depends(get_db)):
    assessment = db.query(Assessment).filter(Assessment.id == id).first()
    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")

    # If the assessment is already analyzed and has become stale, forward to reanalyze to preserve auditability!
    if assessment.status == "ANALYZED" and assessment.is_stale:
        return reanalyze_assessment(id=id, db=db)

    g_doc = (
        db.query(DocumentVersion)
        .filter(DocumentVersion.assessment_id == id, DocumentVersion.doc_type == "guideline", DocumentVersion.is_active == True)
        .order_by(DocumentVersion.version_number.desc())
        .first()
    )
    a_doc = (
        db.query(DocumentVersion)
        .filter(DocumentVersion.assessment_id == id, DocumentVersion.doc_type == "application", DocumentVersion.is_active == True)
        .order_by(DocumentVersion.version_number.desc())
        .first()
    )

    if not g_doc or not a_doc:
        raise HTTPException(
            status_code=400,
            detail="Cannot analyze application: Both a Grant Guideline and Draft Application document must be uploaded."
        )

    _execute_pipeline_for_assessment(assessment, g_doc, a_doc, db)
    return _build_detail_out(assessment, db)

@router.post("/{id}/reanalyze", response_model=AssessmentDetailOut)
def reanalyze_assessment(id: str = Path(..., description="Assessment UUID"), db: Session = Depends(get_db)):
    """
    Re-analysis creates a new assessment run while preserving the previous assessment for auditability.
    """
    prev_assessment = db.query(Assessment).filter(Assessment.id == id).first()
    if not prev_assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")

    # Retrieve latest active documents
    latest_g = (
        db.query(DocumentVersion)
        .filter(DocumentVersion.assessment_id == id, DocumentVersion.doc_type == "guideline", DocumentVersion.is_active == True)
        .order_by(DocumentVersion.version_number.desc())
        .first()
    )
    latest_a = (
        db.query(DocumentVersion)
        .filter(DocumentVersion.assessment_id == id, DocumentVersion.doc_type == "application", DocumentVersion.is_active == True)
        .order_by(DocumentVersion.version_number.desc())
        .first()
    )

    if not latest_g or not latest_a:
        raise HTTPException(
            status_code=400,
            detail="Cannot re-analyze: Both a Grant Guideline and Draft Application document must be present."
        )

    # 1. Create a new assessment run while preserving the previous assessment for auditability
    new_run_number = prev_assessment.run_number + 1
    new_assessment = Assessment(
        title=f"{prev_assessment.grant_name} Review (Run #{new_run_number})",
        grant_name=prev_assessment.grant_name,
        application_name=prev_assessment.application_name,
        status="DRAFT",
        guideline_version=latest_g.version_number,
        application_version=latest_a.version_number,
        run_number=new_run_number,
        parent_assessment_id=prev_assessment.id,
        is_stale=False,
    )
    db.add(new_assessment)
    db.flush()

    # 2. Copy all document history to the new assessment run so all versions are retained
    all_prev_docs = db.query(DocumentVersion).filter(DocumentVersion.assessment_id == prev_assessment.id).all()
    for d in all_prev_docs:
        cloned_doc = DocumentVersion(
            assessment_id=new_assessment.id,
            doc_type=d.doc_type,
            filename=d.filename,
            file_hash=d.file_hash,
            version_number=d.version_number,
            is_active=d.is_active,
            page_count=d.page_count,
            storage_path=d.storage_path,
            upload_timestamp=d.upload_timestamp,
        )
        db.add(cloned_doc)

    # 3. Copy supporting document requirements
    for sup in prev_assessment.supporting_documents:
        cloned_sup = SupportingDocument(
            assessment_id=new_assessment.id,
            name=sup.name,
            is_required=sup.is_required,
            is_supplied=sup.is_supplied,
            filename=sup.filename,
            reviewer_notes=sup.reviewer_notes,
        )
        db.add(cloned_sup)

    db.flush()

    # 4. Find the cloned active documents for the new assessment run
    new_g = (
        db.query(DocumentVersion)
        .filter(DocumentVersion.assessment_id == new_assessment.id, DocumentVersion.doc_type == "guideline", DocumentVersion.is_active == True)
        .first()
    )
    new_a = (
        db.query(DocumentVersion)
        .filter(DocumentVersion.assessment_id == new_assessment.id, DocumentVersion.doc_type == "application", DocumentVersion.is_active == True)
        .first()
    )

    # 5. Execute pipeline on the new assessment run
    _execute_pipeline_for_assessment(new_assessment, new_g, new_a, db)

    return _build_detail_out(new_assessment, db)
