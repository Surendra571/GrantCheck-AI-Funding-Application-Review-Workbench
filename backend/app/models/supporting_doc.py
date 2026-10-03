import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base

class SupportingDocument(Base):
    __tablename__ = "supporting_documents"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    assessment_id = Column(String(36), ForeignKey("assessments.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    is_required = Column(Boolean, nullable=False, default=True)
    is_supplied = Column(Boolean, nullable=False, default=False)
    filename = Column(String(255), nullable=True)
    reviewer_notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    assessment = relationship("Assessment", back_populates="supporting_documents")
