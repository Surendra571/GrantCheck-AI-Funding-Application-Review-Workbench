import pytest
from fastapi import HTTPException
from app.models.assessment import Assessment
from app.models.document import DocumentVersion
from app.services.versioning_service import VersioningService

def test_initial_document_upload_version_1(db_session):
    asm = Assessment(title="Test", grant_name="Grant", application_name="App")
    db_session.add(asm)
    db_session.commit()

    doc1 = VersioningService.register_document(
        db=db_session,
        assessment_id=asm.id,
        doc_type="guideline",
        filename="guideline_v1.txt",
        file_bytes=b"Guideline v1 content text."
    )
    assert doc1.version_number == 1
    assert doc1.is_active is True
    assert asm.is_stale is False

def test_duplicate_upload_raises_error(db_session):
    asm = Assessment(title="Test", grant_name="Grant", application_name="App")
    db_session.add(asm)
    db_session.commit()

    content = b"Exact identical document content."
    VersioningService.register_document(
        db=db_session,
        assessment_id=asm.id,
        doc_type="guideline",
        filename="doc.txt",
        file_bytes=content
    )

    with pytest.raises(HTTPException) as exc:
        VersioningService.register_document(
            db=db_session,
            assessment_id=asm.id,
            doc_type="guideline",
            filename="doc_copy.txt",
            file_bytes=content
        )
    assert exc.value.status_code == 409
    assert "Duplicate upload" in exc.value.detail

def test_new_document_triggers_stale_and_increments_version(db_session):
    asm = Assessment(title="Test", grant_name="Grant", application_name="App")
    db_session.add(asm)
    db_session.commit()

    doc1 = VersioningService.register_document(
        db=db_session,
        assessment_id=asm.id,
        doc_type="guideline",
        filename="guideline_v1.txt",
        file_bytes=b"Initial guideline text."
    )
    assert doc1.version_number == 1

    doc2 = VersioningService.register_document(
        db=db_session,
        assessment_id=asm.id,
        doc_type="guideline",
        filename="guideline_v2.txt",
        file_bytes=b"Amended guideline text with new requirements."
    )
    assert doc2.version_number == 2
    assert doc2.is_active is True

    db_session.refresh(doc1)
    assert doc1.is_active is False

    db_session.refresh(asm)
    assert asm.is_stale is True
    assert "Assessment stale — source document changed" in asm.stale_reason


def test_application_replacement_marks_assessment_stale(db_session):
    assessment = Assessment(title="Test", grant_name="Grant", application_name="App")
    db_session.add(assessment)
    db_session.commit()

    first = VersioningService.register_document(
        db=db_session,
        assessment_id=assessment.id,
        doc_type="application",
        filename="application_v1.txt",
        file_bytes=b"Initial application text.",
    )
    second = VersioningService.register_document(
        db=db_session,
        assessment_id=assessment.id,
        doc_type="application",
        filename="application_v2.txt",
        file_bytes=b"Updated application text with a new budget.",
    )

    db_session.refresh(assessment)
    db_session.refresh(first)
    assert second.version_number == 2
    assert first.is_active is False
    assert assessment.is_stale is True
    assert "Application updated from v1 to v2" in assessment.stale_reason


def test_changing_both_source_documents_reports_both_stale_transitions(db_session):
    assessment = Assessment(
        title="Test",
        grant_name="Grant",
        application_name="App",
        status="ANALYZED",
        guideline_version=1,
        application_version=1,
    )
    db_session.add(assessment)
    db_session.commit()

    initial_documents = [
        ("guideline", "guideline_v1.txt", b"Initial guideline text."),
        ("application", "application_v1.txt", b"Initial application text."),
    ]
    for doc_type, filename, content in initial_documents:
        VersioningService.register_document(
            db=db_session,
            assessment_id=assessment.id,
            doc_type=doc_type,
            filename=filename,
            file_bytes=content,
        )

    guideline_v2 = VersioningService.register_document(
        db=db_session,
        assessment_id=assessment.id,
        doc_type="guideline",
        filename="guideline_v2.txt",
        file_bytes=b"Updated guideline with new eligibility terms.",
    )
    application_v2 = VersioningService.register_document(
        db=db_session,
        assessment_id=assessment.id,
        doc_type="application",
        filename="application_v2.txt",
        file_bytes=b"Updated application with revised project budget.",
    )

    db_session.refresh(assessment)
    assert guideline_v2.version_number == 2
    assert application_v2.version_number == 2
    assert assessment.is_stale is True
    assert "Guideline updated from v1 to v2" in assessment.stale_reason
    assert "Application updated from v1 to v2" in assessment.stale_reason


def test_invalid_replacement_preserves_active_version(db_session):
    assessment = Assessment(title="Test", grant_name="Grant", application_name="App")
    db_session.add(assessment)
    db_session.commit()

    first = VersioningService.register_document(
        db=db_session,
        assessment_id=assessment.id,
        doc_type="guideline",
        filename="guideline_v1.txt",
        file_bytes=b"Valid guideline text.",
    )

    with pytest.raises(ValueError, match="Unsupported file format"):
        VersioningService.register_document(
            db=db_session,
            assessment_id=assessment.id,
            doc_type="guideline",
            filename="replacement.png",
            file_bytes=b"not a guideline",
        )

    db_session.refresh(first)
    db_session.refresh(assessment)
    active_versions = (
        db_session.query(DocumentVersion)
        .filter(
            DocumentVersion.assessment_id == assessment.id,
            DocumentVersion.doc_type == "guideline",
            DocumentVersion.is_active == True,
        )
        .all()
    )
    assert first.is_active is True
    assert active_versions == [first]
    assert assessment.is_stale is False


def test_unchanged_document(db_session):
    asm = Assessment(title="Test Unchanged", grant_name="Grant", application_name="App")
    db_session.add(asm)
    db_session.commit()

    content = b"Constant unchanging document content."
    v1 = VersioningService.register_document(
        db=db_session,
        assessment_id=asm.id,
        doc_type="guideline",
        filename="guideline.txt",
        file_bytes=content,
    )
    assert v1.version_number == 1

    with pytest.raises(HTTPException) as exc:
        VersioningService.register_document(
            db=db_session,
            assessment_id=asm.id,
            doc_type="guideline",
            filename="guideline_copy.txt",
            file_bytes=content,
        )
    assert exc.value.status_code == 409
    assert "Duplicate upload" in exc.value.detail


def test_changed_guideline(db_session):
    asm = Assessment(title="Test Guideline Change", grant_name="Grant", application_name="App", status="ANALYZED", guideline_version=1, application_version=1)
    db_session.add(asm)
    db_session.commit()

    g1 = VersioningService.register_document(
        db=db_session,
        assessment_id=asm.id,
        doc_type="guideline",
        filename="g1.txt",
        file_bytes=b"Guideline content version 1",
    )
    assert g1.version_number == 1

    g2 = VersioningService.register_document(
        db=db_session,
        assessment_id=asm.id,
        doc_type="guideline",
        filename="g2.txt",
        file_bytes=b"Guideline content version 2 with amendments",
    )
    assert g2.version_number == 2
    assert g2.is_active is True

    db_session.refresh(g1)
    assert g1.is_active is False

    db_session.refresh(asm)
    assert asm.is_stale is True
    assert "Assessment stale" in asm.stale_reason


def test_changed_application(db_session):
    asm = Assessment(title="Test App Change", grant_name="Grant", application_name="App", status="ANALYZED", guideline_version=1, application_version=1)
    db_session.add(asm)
    db_session.commit()

    a1 = VersioningService.register_document(
        db=db_session,
        assessment_id=asm.id,
        doc_type="application",
        filename="a1.txt",
        file_bytes=b"Application content version 1",
    )
    assert a1.version_number == 1

    a2 = VersioningService.register_document(
        db=db_session,
        assessment_id=asm.id,
        doc_type="application",
        filename="a2.txt",
        file_bytes=b"Application content version 2 with updated budget",
    )
    assert a2.version_number == 2
    assert a2.is_active is True

    db_session.refresh(a1)
    assert a1.is_active is False

    db_session.refresh(asm)
    assert asm.is_stale is True


def test_changed_both(db_session):
    asm = Assessment(title="Test Both Change", grant_name="Grant", application_name="App", status="ANALYZED", guideline_version=1, application_version=1)
    db_session.add(asm)
    db_session.commit()

    VersioningService.register_document(
        db=db_session, assessment_id=asm.id, doc_type="guideline", filename="g1.txt", file_bytes=b"g1"
    )
    VersioningService.register_document(
        db=db_session, assessment_id=asm.id, doc_type="application", filename="a1.txt", file_bytes=b"a1"
    )

    g2 = VersioningService.register_document(
        db=db_session, assessment_id=asm.id, doc_type="guideline", filename="g2.txt", file_bytes=b"g2 new"
    )
    a2 = VersioningService.register_document(
        db=db_session, assessment_id=asm.id, doc_type="application", filename="a2.txt", file_bytes=b"a2 new"
    )

    assert g2.version_number == 2
    assert a2.version_number == 2
    db_session.refresh(asm)
    assert asm.is_stale is True


def test_multiple_versions(db_session):
    asm = Assessment(title="Test Multiple Versions", grant_name="Grant", application_name="App")
    db_session.add(asm)
    db_session.commit()

    v1 = VersioningService.register_document(db=db_session, assessment_id=asm.id, doc_type="guideline", filename="g.txt", file_bytes=b"v1")
    v2 = VersioningService.register_document(db=db_session, assessment_id=asm.id, doc_type="guideline", filename="g.txt", file_bytes=b"v2")
    v3 = VersioningService.register_document(db=db_session, assessment_id=asm.id, doc_type="guideline", filename="g.txt", file_bytes=b"v3")

    all_v = db_session.query(DocumentVersion).filter(
        DocumentVersion.assessment_id == asm.id, DocumentVersion.doc_type == "guideline"
    ).order_by(DocumentVersion.version_number.asc()).all()

    assert len(all_v) == 3
    assert [d.version_number for d in all_v] == [1, 2, 3]
    assert [d.is_active for d in all_v] == [False, False, True]


def test_stale_detection(db_session):
    asm = Assessment(title="Test Direct Stale", grant_name="Grant", application_name="App", guideline_version=1, application_version=1, is_stale=False)
    db_session.add(asm)
    db_session.commit()

    g = DocumentVersion(assessment_id=asm.id, doc_type="guideline", filename="g.txt", file_hash="hash1", version_number=2, is_active=True, page_count=1, storage_path="/path1")
    a = DocumentVersion(assessment_id=asm.id, doc_type="application", filename="a.txt", file_hash="hash2", version_number=1, is_active=True, page_count=1, storage_path="/path2")
    db_session.add_all([g, a])
    db_session.commit()

    is_stale = VersioningService.check_and_update_stale_status(db_session, asm)
    assert is_stale is True
    assert asm.is_stale is True


def test_reanalysis(db_session):
    from app.api.assessments import reanalyze_assessment

    asm = Assessment(
        title="Test Reanalysis Run",
        grant_name="UK CleanTech",
        application_name="Filter Clean Proposal",
        status="ANALYZED",
        guideline_version=1,
        application_version=1,
        run_number=1,
        is_stale=True,
    )
    db_session.add(asm)
    db_session.commit()

    VersioningService.register_document(db=db_session, assessment_id=asm.id, doc_type="guideline", filename="g1.txt", file_bytes=b"Eligibility: Lead applicant must be a UK SME.")
    VersioningService.register_document(db=db_session, assessment_id=asm.id, doc_type="application", filename="a1.txt", file_bytes=b"Applicant is a UK SME.")
    VersioningService.register_document(db=db_session, assessment_id=asm.id, doc_type="guideline", filename="g2.txt", file_bytes=b"Eligibility: Lead applicant must be a UK SME with 2 years records.")

    new_run = reanalyze_assessment(id=asm.id, db=db_session)

    db_session.refresh(asm)
    assert asm.status == "ANALYZED"
    assert asm.run_number == 1

    assert new_run.id != asm.id
    assert new_run.run_number == 2
    assert new_run.parent_assessment_id == asm.id
    assert new_run.guideline_version == 2
    assert new_run.application_version == 1
    assert new_run.is_stale is False
    assert new_run.status == "ANALYZED"

