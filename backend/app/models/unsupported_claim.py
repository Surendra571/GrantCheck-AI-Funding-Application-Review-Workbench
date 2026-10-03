import uuid
from sqlalchemy import Column, String, Integer, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base

class UnsupportedClaim(Base):
    __tablename__ = "unsupported_claims"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    assessment_id = Column(String(36), ForeignKey("assessments.id", ondelete="CASCADE"), nullable=False)
    claim = Column(Text, nullable=False)
    source_page = Column(Integer, nullable=True)
    reason = Column(Text, nullable=False)
    related_requirement = Column(String(50), nullable=True)
    status = Column(String(100), nullable=False, default="No supporting evidence found in supplied materials")

    assessment = relationship("Assessment", back_populates="unsupported_claims")

class ClarificationQuestion(Base):
    __tablename__ = "clarification_questions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    assessment_id = Column(String(36), ForeignKey("assessments.id", ondelete="CASCADE"), nullable=False)
    requirement_id = Column(String(50), nullable=True)
    question = Column(Text, nullable=False)
    gap_type = Column(String(50), nullable=False)  # MISSING, WEAK, AMBIGUOUS
    suggested_evidence = Column(Text, nullable=False)

    assessment = relationship("Assessment", back_populates="clarification_questions")
