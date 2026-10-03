from typing import List
from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.assessment import Assessment
from app.models.supporting_doc import SupportingDocument
from app.schemas.assessment import SupportingDocCreate, SupportingDocUpdate, SupportingDocOut

router = APIRouter(prefix="/assessments/{assessment_id}/supporting-docs", tags=["Supporting Documents"])

@router.get("", response_model=List[SupportingDocOut])
def list_supporting_docs(
    assessment_id: str = Path(..., description="Assessment UUID"),
    db: Session = Depends(get_db),
):
    return (
        db.query(SupportingDocument)
        .filter(SupportingDocument.assessment_id == assessment_id)
        .order_by(SupportingDocument.created_at.asc())
        .all()
    )

@router.post("", response_model=SupportingDocOut, status_code=201)
def add_supporting_doc(
    assessment_id: str = Path(..., description="Assessment UUID"),
    doc_in: SupportingDocCreate = ...,
    db: Session = Depends(get_db),
):
    assessment = db.query(Assessment).filter(Assessment.id == assessment_id).first()
    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")

    new_doc = SupportingDocument(
        assessment_id=assessment_id,
        name=doc_in.name.strip(),
        is_required=doc_in.is_required,
        is_supplied=doc_in.is_supplied,
        filename=doc_in.filename,
        reviewer_notes=doc_in.reviewer_notes,
    )
    db.add(new_doc)
    db.commit()
    db.refresh(new_doc)
    return new_doc

@router.patch("/{doc_id}", response_model=SupportingDocOut)
def update_supporting_doc(
    assessment_id: str = Path(..., description="Assessment UUID"),
    doc_id: str = Path(..., description="Supporting Doc UUID"),
    doc_in: SupportingDocUpdate = ...,
    db: Session = Depends(get_db),
):
    doc = (
        db.query(SupportingDocument)
        .filter(SupportingDocument.assessment_id == assessment_id, SupportingDocument.id == doc_id)
        .first()
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Supporting document requirement not found")

    if doc_in.is_supplied is not None:
        doc.is_supplied = doc_in.is_supplied
    if doc_in.filename is not None:
        doc.filename = doc_in.filename
    if doc_in.reviewer_notes is not None:
        doc.reviewer_notes = doc_in.reviewer_notes

    db.commit()
    db.refresh(doc)
    return doc

@router.delete("/{doc_id}", status_code=204)
def delete_supporting_doc(
    assessment_id: str = Path(..., description="Assessment UUID"),
    doc_id: str = Path(..., description="Supporting Doc UUID"),
    db: Session = Depends(get_db),
):
    doc = (
        db.query(SupportingDocument)
        .filter(SupportingDocument.assessment_id == assessment_id, SupportingDocument.id == doc_id)
        .first()
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Supporting document not found")

    db.delete(doc)
    db.commit()
    return None
