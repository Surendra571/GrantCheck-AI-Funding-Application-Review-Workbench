from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
from app.schemas.score import DeterministicScoreBreakdown
from app.schemas.ai import UnsupportedClaimItem, ClarificationQuestionItem

class DocumentVersionOut(BaseModel):
    id: str
    doc_type: str
    filename: str
    file_hash: str
    version_number: int
    is_active: bool
    page_count: int
    upload_timestamp: datetime

class SupportingDocCreate(BaseModel):
    name: str
    is_required: bool = True
    is_supplied: bool = False
    filename: Optional[str] = None
    reviewer_notes: Optional[str] = None

class SupportingDocUpdate(BaseModel):
    is_supplied: Optional[bool] = None
    filename: Optional[str] = None
    reviewer_notes: Optional[str] = None

class SupportingDocOut(BaseModel):
    id: str
    name: str
    is_required: bool
    is_supplied: bool
    filename: Optional[str] = None
    reviewer_notes: Optional[str] = None

class RequirementDetailOut(BaseModel):
    id: str
    req_id_code: str
    text: str
    type: str
    mandatory: bool
    category: str
    source_document: str
    source_page: Optional[int] = None
    source_section: Optional[str] = None
    source_excerpt: str

    # AI assessment fields (Preserved)
    mapping_id: Optional[str] = None
    ai_status: Optional[str] = None
    evidence: Optional[str] = None
    evidence_source_doc: Optional[str] = None
    evidence_page: Optional[int] = None
    evidence_section: Optional[str] = None
    confidence: Optional[float] = None
    reasoning: Optional[str] = None

    # Reviewer decision fields
    reviewer_decision: str = "PENDING"
    reviewer_override_status: Optional[str] = None
    reviewer_notes: Optional[str] = None
    reviewer_evidence: Optional[str] = None
    reviewer_citation: Optional[str] = None
    reviewed_at: Optional[datetime] = None

    # Final assessment fields
    effective_status: str
    is_final_complete: bool

class AssessmentCreate(BaseModel):
    title: Optional[str] = None
    grant_name: str
    application_name: str

class AssessmentListItem(BaseModel):
    id: str
    title: str
    grant_name: str
    application_name: str
    status: str
    guideline_version: int = 1
    application_version: int = 1
    run_number: int = 1
    parent_assessment_id: Optional[str] = None
    is_stale: bool
    stale_reason: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    completion_percentage: Optional[float] = 0.0

class AssessmentDetailOut(BaseModel):
    id: str
    title: str
    grant_name: str
    application_name: str
    status: str
    guideline_version: int = 1
    application_version: int = 1
    run_number: int = 1
    parent_assessment_id: Optional[str] = None
    is_stale: bool
    stale_reason: Optional[str] = None
    raw_analysis_payload: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime

    active_guideline: Optional[DocumentVersionOut] = None
    active_application: Optional[DocumentVersionOut] = None
    document_versions: List[DocumentVersionOut] = []

    score: Optional[DeterministicScoreBreakdown] = None
    requirements: List[RequirementDetailOut] = []
    supporting_documents: List[SupportingDocOut] = []

class ReviewedSummaryReportOut(BaseModel):
    assessment_id: str
    grant_name: str
    application_name: str
    guideline_version: int
    application_version: int
    guideline_hash: str
    application_hash: str
    run_number: int = 1
    is_stale: bool
    stale_reason: Optional[str] = None
    score: DeterministicScoreBreakdown
    unsupported_claims: List[UnsupportedClaimItem]
    missing_documents: List[SupportingDocOut]
    clarification_questions: List[ClarificationQuestionItem]
    reviewer_decisions_summary: Dict[str, int]
    raw_ai_audit_snapshot: Optional[Dict[str, Any]] = None
    disclaimer: str
