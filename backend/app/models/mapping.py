import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Float, Integer, Text, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from app.database import Base

class RequirementMapping(Base):
    __tablename__ = "requirement_mappings"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    requirement_id = Column(String(36), ForeignKey("requirements.id", ondelete="CASCADE"), nullable=False, unique=True)

    # Original AI-generated mapping fields (Preserved)
    ai_status = Column(String(50), nullable=False)  # SUPPORTED, WEAK, MISSING, AMBIGUOUS
    evidence = Column(Text, nullable=True)
    source_document = Column(String(255), nullable=True)
    source_page = Column(Integer, nullable=True)
    source_section = Column(String(255), nullable=True)
    confidence = Column(Float, nullable=False, default=1.0)
    reasoning = Column(Text, nullable=True)

    # Human Reviewer Fields
    reviewer_decision = Column(String(50), nullable=False, default="PENDING")  # PENDING, CONFIRMED, CORRECTED, REJECTED
    reviewer_override_status = Column(String(50), nullable=True)  # SUPPORTED, WEAK, MISSING, AMBIGUOUS
    reviewer_notes = Column(Text, nullable=True)
    reviewer_evidence = Column(Text, nullable=True)
    reviewer_citation = Column(String(255), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)

    requirement = relationship("Requirement", back_populates="mapping")

    @property
    def effective_status(self) -> str:
        if self.reviewer_decision == "CONFIRMED":
            return "SUPPORTED"
        if self.reviewer_decision == "REJECTED":
            return "MISSING"
        if self.reviewer_decision == "CORRECTED":
            return self.reviewer_override_status or "SUPPORTED"
        return self.ai_status

    @property
    def is_final_complete(self) -> bool:
        return self.effective_status == "SUPPORTED"
