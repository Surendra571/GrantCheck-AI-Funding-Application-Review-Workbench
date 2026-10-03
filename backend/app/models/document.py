import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Boolean, DateTime, Integer, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base

class DocumentVersion(Base):
    __tablename__ = "document_versions"

    # Document ID (UUID)
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    assessment_id = Column(String(36), ForeignKey("assessments.id", ondelete="CASCADE"), nullable=False)

    # Document metadata & versioning
    doc_type = Column(String(50), nullable=False)  # 'guideline', 'application', 'supporting'
    filename = Column(String(255), nullable=False)
    file_hash = Column(String(64), nullable=False)  # SHA-256 content hash
    version_number = Column(Integer, nullable=False, default=1)
    is_active = Column(Boolean, nullable=False, default=True)
    page_count = Column(Integer, nullable=False, default=1)
    storage_path = Column(String(512), nullable=False)

    # Uploaded timestamp
    upload_timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    assessment = relationship("Assessment", back_populates="documents")
