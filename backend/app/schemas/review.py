from typing import Optional, Literal
from datetime import datetime
from pydantic import BaseModel, Field, model_validator
from app.schemas.score import DeterministicScoreBreakdown

ReviewerDecisionType = Literal["CONFIRMED", "CORRECTED", "REJECTED"]
ReviewerOverrideStatusType = Literal["SUPPORTED", "WEAK", "MISSING", "AMBIGUOUS"]

class ReviewSubmissionRequest(BaseModel):
    decision: ReviewerDecisionType = Field(..., description="Reviewer decision: CONFIRMED, CORRECTED, or REJECTED")
    override_status: Optional[ReviewerOverrideStatusType] = Field(None, description="New status if corrected")
    reviewer_notes: Optional[str] = Field(None, description="Reviewer explanation (mandatory for CORRECTED and REJECTED)")
    override_evidence: Optional[str] = Field(None, description="Optional updated evidence excerpt")
    override_citation: Optional[str] = Field(None, description="Optional updated citation")

    @model_validator(mode="after")
    def validate_notes_requirement(self):
        if self.decision in ("CORRECTED", "REJECTED"):
            if not self.reviewer_notes or not self.reviewer_notes.strip():
                raise ValueError(f"Reviewer notes are mandatory when decision is {self.decision}.")
        if self.decision == "CORRECTED" and not self.override_status:
            raise ValueError("An override status must be specified when decision is CORRECTED.")
        return self

class ReviewSubmissionResponse(BaseModel):
    mapping_id: str
    requirement_id: str
    ai_status: str
    reviewer_decision: str
    reviewer_override_status: Optional[str] = None
    effective_status: str
    reviewer_notes: Optional[str] = None
    reviewed_at: datetime
    recalculated_score: DeterministicScoreBreakdown
    message: str
