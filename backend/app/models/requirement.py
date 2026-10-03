import uuid
from sqlalchemy import Column, String, Boolean, Integer, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base

class Requirement(Base):
    __tablename__ = "requirements"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    assessment_id = Column(String(36), ForeignKey("assessments.id", ondelete="CASCADE"), nullable=False)
    req_id_code = Column(String(50), nullable=False)
    text = Column(Text, nullable=False)
    type = Column(String(50), nullable=False)  # mandatory, recommendation, eligibility-related, submission-related
    mandatory = Column(Boolean, nullable=False, default=True)
    category = Column(String(50), nullable=False)  # eligibility, submission, documentation, project, financial, organisation, recommendation, other
    source_document = Column(String(255), nullable=False)
    source_page = Column(Integer, nullable=True)
    source_section = Column(String(255), nullable=True)
    source_excerpt = Column(Text, nullable=False)

    assessment = relationship("Assessment", back_populates="requirements")
    mapping = relationship("RequirementMapping", back_populates="requirement", uselist=False, cascade="all, delete-orphan")
