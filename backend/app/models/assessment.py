import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Boolean, DateTime, Integer, Text, JSON, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base

class Assessment(Base):
    __tablename__ = "assessments"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String(255), nullable=False)
    grant_name = Column(String(255), nullable=False)
    application_name = Column(String(255), nullable=False)
    status = Column(String(50), nullable=False, default="DRAFT")  # DRAFT, ANALYZING, ANALYZED, ARCHIVED, ERROR

    # Document version tracking on the assessment run
    guideline_version = Column(Integer, nullable=False, default=1)
    application_version = Column(Integer, nullable=False, default=1)

    # Stale detection
    is_stale = Column(Boolean, nullable=False, default=False)
    stale_reason = Column(Text, nullable=True)

    # Re-analysis and auditability tracking
    run_number = Column(Integer, nullable=False, default=1)
    parent_assessment_id = Column(String(36), ForeignKey("assessments.id", ondelete="SET NULL"), nullable=True)

    raw_analysis_payload = Column(JSON, nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    documents = relationship("DocumentVersion", back_populates="assessment", cascade="all, delete-orphan", order_by="DocumentVersion.version_number")
    requirements = relationship("Requirement", back_populates="assessment", cascade="all, delete-orphan", order_by="Requirement.req_id_code")
    supporting_documents = relationship("SupportingDocument", back_populates="assessment", cascade="all, delete-orphan")
    unsupported_claims = relationship("UnsupportedClaim", back_populates="assessment", cascade="all, delete-orphan")
    clarification_questions = relationship("ClarificationQuestion", back_populates="assessment", cascade="all, delete-orphan")

    # Parent/child relationship for re-analysis runs
    previous_runs = relationship("Assessment", backref="latest_run", remote_side=[id])
