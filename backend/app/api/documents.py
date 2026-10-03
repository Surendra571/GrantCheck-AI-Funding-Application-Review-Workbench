from typing import List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Path
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.document import DocumentVersion
from app.schemas.assessment import DocumentVersionOut
from app.services.versioning_service import VersioningService

router = APIRouter(prefix="/assessments/{assessment_id}/documents", tags=["Documents"])

@router.post("/upload", response_model=DocumentVersionOut)
async def upload_document(
    assessment_id: str = Path(..., description="Assessment UUID"),
    doc_type: str = Form(..., description="'guideline', 'application', or 'supporting'"),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    if doc_type not in ("guideline", "application", "supporting"):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid doc_type '{doc_type}'. Allowed: 'guideline', 'application', 'supporting'."
        )

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    try:
        new_doc, _ = VersioningService.register_document(
            db=db,
            assessment_id=assessment_id,
            doc_type=doc_type,
            filename=file.filename or "uploaded_document",
            file_bytes=content,
        )
        return new_doc
    except ValueError as e:
        raise HTTPException(status_code=415, detail=str(e))

@router.get("", response_model=List[DocumentVersionOut])
def list_documents(
    assessment_id: str = Path(..., description="Assessment UUID"),
    db: Session = Depends(get_db),
):
    return (
        db.query(DocumentVersion)
        .filter(DocumentVersion.assessment_id == assessment_id)
        .order_by(DocumentVersion.upload_timestamp.desc())
        .all()
    )
