import os
from sqlalchemy.orm import Session
from fastapi import HTTPException
from app.config import settings
from app.models.document import DocumentVersion
from app.models.assessment import Assessment
from app.services.parser import DocumentParser

class VersioningService:
    @classmethod
    def register_document(
        cls,
        db: Session,
        assessment_id: str,
        doc_type: str,
        filename: str,
        file_bytes: bytes
    ) -> DocumentVersion:
        """
        Uploads and registers a document version.
        Duplicate content is rejected; changed content creates a new version
        while preserving the previous version and marking the assessment stale.
        """
        assessment = db.query(Assessment).filter(Assessment.id == assessment_id).first()
        if not assessment:
            raise HTTPException(status_code=404, detail="Assessment not found")

        file_hash = DocumentParser.compute_sha256(file_bytes)

        # Get current active (latest) document of this type for this assessment
        latest_doc = (
            db.query(DocumentVersion)
            .filter(
                DocumentVersion.assessment_id == assessment_id,
                DocumentVersion.doc_type == doc_type,
                DocumentVersion.is_active == True,
            )
            .order_by(DocumentVersion.version_number.desc())
            .first()
        )

        if latest_doc and latest_doc.file_hash == file_hash:
            raise HTTPException(
                status_code=409,
                detail=f"Duplicate upload: content matches active {doc_type} version {latest_doc.version_number}.",
            )

        # Parse before changing the active version so invalid input has no side effects.
        parsed = DocumentParser.parse(file_bytes, filename)

        if latest_doc:
            latest_doc.is_active = False
            next_version = latest_doc.version_number + 1
        else:
            next_version = 1

        # Save to disk storage
        os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
        storage_filename = f"{assessment_id}_{doc_type}_v{next_version}_{filename}"
        storage_path = os.path.join(settings.UPLOAD_DIR, storage_filename)
        with open(storage_path, "wb") as f:
            f.write(file_bytes)

        new_doc = DocumentVersion(
            assessment_id=assessment_id,
            doc_type=doc_type,
            filename=filename,
            file_hash=file_hash,
            version_number=next_version,
            is_active=True,
            page_count=parsed.page_count,
            storage_path=storage_path,
        )
        db.add(new_doc)
        db.flush()

        # 5. Check if assessment is now stale:
        # If either assessment version no longer matches the latest document version:
        # is_stale = true
        cls.check_and_update_stale_status(db, assessment)

        db.commit()
        db.refresh(new_doc)
        db.refresh(assessment)

        return new_doc

    @classmethod
    def check_and_update_stale_status(cls, db: Session, assessment: Assessment) -> bool:
        """
        If either guideline_version or application_version stored on the assessment
        no longer matches the latest document version, mark is_stale = True.
        """
        latest_g = (
            db.query(DocumentVersion)
            .filter(
                DocumentVersion.assessment_id == assessment.id,
                DocumentVersion.doc_type == "guideline",
                DocumentVersion.is_active == True,
            )
            .order_by(DocumentVersion.version_number.desc())
            .first()
        )
        latest_a = (
            db.query(DocumentVersion)
            .filter(
                DocumentVersion.assessment_id == assessment.id,
                DocumentVersion.doc_type == "application",
                DocumentVersion.is_active == True,
            )
            .order_by(DocumentVersion.version_number.desc())
            .first()
        )

        is_stale = False
        reasons = []

        if latest_g and assessment.guideline_version != latest_g.version_number:
            is_stale = True
            reasons.append(f"Guideline updated from v{assessment.guideline_version} to v{latest_g.version_number}")

        if latest_a and assessment.application_version != latest_a.version_number:
            is_stale = True
            reasons.append(f"Application updated from v{assessment.application_version} to v{latest_a.version_number}")

        if is_stale:
            assessment.is_stale = True
            assessment.stale_reason = "Assessment stale — source document changed. " + "; ".join(reasons)
        return is_stale
