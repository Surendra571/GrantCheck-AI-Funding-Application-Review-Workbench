from typing import List, Optional, Literal
from pydantic import BaseModel, Field

RequirementCategory = Literal[
    "eligibility",
    "submission",
    "documentation",
    "project",
    "financial",
    "organisation",
    "recommendation",
    "other",
]

RequirementType = Literal[
    "mandatory",
    "recommendation",
    "eligibility-related",
    "submission-related",
]

MappingStatus = Literal[
    "SUPPORTED",
    "WEAK",
    "MISSING",
    "AMBIGUOUS",
]

class RequirementExtracted(BaseModel):
    id: str = Field(..., description="Unique requirement identifier, e.g. REQ-001")
    text: str = Field(..., description="Full requirement text")
    type: RequirementType = Field(..., description="Classification of requirement")
    mandatory: bool = Field(..., description="Whether this requirement is strictly mandatory")
    category: RequirementCategory = Field(..., description="Requirement category")
    source_document: str = Field("guideline", description="Document source")
    source_page: Optional[int] = Field(None, description="Page number where requirement appears")
    source_section: Optional[str] = Field(None, description="Section heading")
    source_excerpt: str = Field(..., description="Verbatim quote or excerpt from the guideline")

class RequirementExtractionResponse(BaseModel):
    requirements: List[RequirementExtracted]

class EvidenceCandidate(BaseModel):
    requirement_id: str
    relevant_chunks: List[str]
    pages: List[int]
    sections: List[str]

class EvidenceRetrievalResponse(BaseModel):
    candidates: List[EvidenceCandidate]

class RequirementMappingItem(BaseModel):
    requirement_id: str
    status: MappingStatus
    evidence: Optional[str] = None
    source_document: str = "application"
    source_page: Optional[int] = None
    source_section: Optional[str] = None
    confidence: float = Field(1.0, ge=0.0, le=1.0)
    reasoning: str

class RequirementMappingResponse(BaseModel):
    mappings: List[RequirementMappingItem]

class UnsupportedClaimItem(BaseModel):
    claim: str
    source_page: Optional[int] = None
    reason: str
    related_requirement: Optional[str] = None
    status: str = "No supporting evidence found in supplied materials"

class UnsupportedClaimResponse(BaseModel):
    claims: List[UnsupportedClaimItem]

class ClarificationQuestionItem(BaseModel):
    requirement_id: Optional[str] = None
    question: str
    gap_type: Literal["MISSING", "WEAK", "AMBIGUOUS"]
    suggested_evidence: str

class ClarificationQuestionResponse(BaseModel):
    questions: List[ClarificationQuestionItem]

class PipelineAuditSnapshot(BaseModel):
    guideline_filename: str
    application_filename: str
    guideline_pages: int
    application_pages: int
    extracted_requirements: List[RequirementExtracted]
    mappings: List[RequirementMappingItem]
    unsupported_claims: List[UnsupportedClaimItem]
    clarification_questions: List[ClarificationQuestionItem]
