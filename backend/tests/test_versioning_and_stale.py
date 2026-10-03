import pytest
from fastapi import HTTPException
from app.models.assessment import Assessment
from app.models.document import DocumentVersion
from app.services.versioning_service import VersioningService
from app.api.assessments import reanalyze_assessment

def test_initial_document_upload_version_1(db_session):
    asm = Assessment(title="Test Assessment", grant_name="Grant A", application_name="App A")
    db_session.add(asm)
    db_session.commit()

    doc1, is_new = VersioningService.register_document(
        db=db_session,
        assessment_id=asm.id,
        doc_type="guideline",
        filename="guideline_v1.txt",
        file_bytes=b"Guideline v1 content text."
    )
    assert is_new is True
    assert doc1.version_number == 1
    assert doc1.is_active is True
    assert doc1.filename == "guideline_v1.txt"
    assert len(doc1.file_hash) == 64

def test_unchanged_document_no_duplicate_version(db_session):
    """
    If unchanged, calculate SHA-256, compare against latest version:
    Do not create a duplicate version, return the existing active version.
    """
    asm = Assessment(title="Test", grant_name="Grant", application_name="App")
    db_session.add(asm)
    db_session.commit()

    content = b"Exact identical guideline document content."
    doc1, is_new1 = VersioningService.register_document(
        db=db_session,
        assessment_id=asm.id,
        doc_type="guideline",
        filename="guideline.txt",
        file_bytes=content
    )
    assert is_new1 is True
    assert doc1.version_number == 1

    # Upload identical bytes with different or same filename
    doc2, is_new2 = VersioningService.register_document(
        db=db_session,
        assessment_id=asm.id,
        doc_type="guideline",
        filename="guideline_reupload.txt",
        file_bytes=content
    )
    assert is_new2 is False
    assert doc2.id == doc1.id
    assert doc2.version_number == 1

    # Total versions in database must remain 1
    total_docs = db_session.query(DocumentVersion).filter(
        DocumentVersion.assessment_id == asm.id,
        DocumentVersion.doc_type == "guideline"
    ).count()
    assert total_docs == 1

def test_changed_guideline_triggers_stale(db_session):
    """
    When guideline is updated, previous version is preserved (never deleted),
    new version is created, and the assessment is marked stale.
    """
    asm = Assessment(title="Test", grant_name="Grant", application_name="App", status="ANALYZED", guideline_version=1, application_version=1)
    db_session.add(asm)
    db_session.commit()

    doc1, _ = VersioningService.register_document(
        db=db_session,
        assessment_id=asm.id,
        doc_type="guideline",
        filename="guideline_v1.txt",
        file_bytes=b"Guideline Version 1"
    )
    assert doc1.version_number == 1

    # Upload modified guideline
    doc2, is_new = VersioningService.register_document(
        db=db_session,
        assessment_id=asm.id,
        doc_type="guideline",
        filename="guideline_v2.txt",
        file_bytes=b"Guideline Version 2 with new eligibility criteria"
    )
    assert is_new is True
    assert doc2.version_number == 2
    assert doc2.is_active is True

    # Previous version must still exist
    db_session.refresh(doc1)
    assert doc1.is_active is False
    assert doc1.version_number == 1

    # Assessment must be marked stale
    db_session.refresh(asm)
    assert asm.is_stale is True
    assert "Assessment is stale because a source document changed." in asm.stale_reason

def test_changed_application_triggers_stale(db_session):
    """
    When application document is updated, the assessment is marked stale.
    """
    asm = Assessment(title="Test", grant_name="Grant", application_name="App", status="ANALYZED", guideline_version=1, application_version=1)
    db_session.add(asm)
    db_session.commit()

    app1, _ = VersioningService.register_document(
        db=db_session,
        assessment_id=asm.id,
        doc_type="application",
        filename="application_v1.txt",
        file_bytes=b"Draft Application Section 1"
    )
    assert app1.version_number == 1

    # Upload modified application
    app2, is_new = VersioningService.register_document(
        db=db_session,
        assessment_id=asm.id,
        doc_type="application",
        filename="application_v2.txt",
        file_bytes=b"Draft Application Section 1 amended with updated budget details"
    )
    assert is_new is True
    assert app2.version_number == 2
    assert app2.is_active is True

    db_session.refresh(app1)
    assert app1.is_active is False

    db_session.refresh(asm)
    assert asm.is_stale is True
    assert "Assessment is stale because a source document changed." in asm.stale_reason

def test_changed_both_documents_triggers_stale(db_session):
    """
    Updating both guideline and application creates new versions for each
    and keeps the assessment marked stale.
    """
    asm = Assessment(title="Test", grant_name="Grant", application_name="App", status="ANALYZED", guideline_version=1, application_version=1)
    db_session.add(asm)
    db_session.commit()

    VersioningService.register_document(
        db=db_session,
        assessment_id=asm.id,
        doc_type="guideline",
        filename="g_v1.txt",
        file_bytes=b"Guideline v1"
    )
    VersioningService.register_document(
        db=db_session,
        assessment_id=asm.id,
        doc_type="application",
        filename="a_v1.txt",
        file_bytes=b"Application v1"
    )

    # Now upload v2 for guideline
    g2, _ = VersioningService.register_document(
        db=db_session,
        assessment_id=asm.id,
        doc_type="guideline",
        filename="g_v2.txt",
        file_bytes=b"Guideline v2 new content"
    )
    # Now upload v2 for application
    a2, _ = VersioningService.register_document(
        db=db_session,
        assessment_id=asm.id,
        doc_type="application",
        filename="a_v2.txt",
        file_bytes=b"Application v2 new content"
    )

    assert g2.version_number == 2
    assert a2.version_number == 2

    db_session.refresh(asm)
    assert asm.is_stale is True
    assert asm.guideline_version == 1
    assert asm.application_version == 1

def test_multiple_versions_preserved_in_history(db_session):
    """
    Verify that repeated updates preserve all previous versions without deleting.
    """
    asm = Assessment(title="Test Multi", grant_name="Grant", application_name="App")
    db_session.add(asm)
    db_session.commit()

    v1, _ = VersioningService.register_document(db=db_session, assessment_id=asm.id, doc_type="guideline", filename="g.txt", file_bytes=b"Version 1")
    v2, _ = VersioningService.register_document(db=db_session, assessment_id=asm.id, doc_type="guideline", filename="g.txt", file_bytes=b"Version 2")
    v3, _ = VersioningService.register_document(db=db_session, assessment_id=asm.id, doc_type="guideline", filename="g.txt", file_bytes=b"Version 3")

    all_versions = db_session.query(DocumentVersion).filter(
        DocumentVersion.assessment_id == asm.id,
        DocumentVersion.doc_type == "guideline"
    ).order_by(DocumentVersion.version_number.asc()).all()

    assert len(all_versions) == 3
    assert [v.version_number for v in all_versions] == [1, 2, 3]
    assert [v.is_active for v in all_versions] == [False, False, True]

def test_stale_detection_when_versions_mismatch(db_session):
    """
    Verify check_and_update_stale_status detects version mismatch correctly.
    """
    asm = Assessment(title="Test Stale", grant_name="Grant", application_name="App", guideline_version=1, application_version=1, is_stale=False)
    db_session.add(asm)
    db_session.commit()

    # Create active guideline with version 2
    doc_g = DocumentVersion(
        assessment_id=asm.id,
        doc_type="guideline",
        filename="guideline_v2.txt",
        file_hash="dummy_hash_1",
        version_number=2,
        is_active=True,
        page_count=3,
        storage_path="path/to/v2"
    )
    doc_a = DocumentVersion(
        assessment_id=asm.id,
        doc_type="application",
        filename="application_v1.txt",
        file_hash="dummy_hash_2",
        version_number=1,
        is_active=True,
        page_count=5,
        storage_path="path/to/v1"
    )
    db_session.add_all([doc_g, doc_a])
    db_session.commit()

    is_stale = VersioningService.check_and_update_stale_status(db_session, asm)
    assert is_stale is True
    assert asm.is_stale is True
    assert asm.stale_reason == "Assessment is stale because a source document changed."

def test_reanalysis_creates_new_assessment_run_and_preserves_previous(db_session):
    """
    Re-analysis must create a new assessment run (run_number = 2, parent_assessment_id = run 1)
    while preserving the previous assessment run completely for auditability.
    """
    # 1. Setup initial assessment
    asm1 = Assessment(
        title="Community Grant Review",
        grant_name="Community Grant",
        application_name="Project Oasis",
        status="ANALYZED",
        guideline_version=1,
        application_version=1,
        run_number=1,
        is_stale=True,
        stale_reason="Assessment is stale because a source document changed."
    )
    db_session.add(asm1)
    db_session.commit()

    # Add v1 guideline and v1 application
    g1, _ = VersioningService.register_document(
        db=db_session,
        assessment_id=asm1.id,
        doc_type="guideline",
        filename="guideline_v1.txt",
        file_bytes=b"Eligible entities must be registered non-profits."
    )
    a1, _ = VersioningService.register_document(
        db=db_session,
        assessment_id=asm1.id,
        doc_type="application",
        filename="app_v1.txt",
        file_bytes=b"Project Oasis is an unincorporated community group."
    )

    # Now upload v2 guideline (stale trigger)
    g2, _ = VersioningService.register_document(
        db=db_session,
        assessment_id=asm1.id,
        doc_type="guideline",
        filename="guideline_v2.txt",
        file_bytes=b"Eligible entities must be registered non-profits or community trusts."
    )
    assert g2.version_number == 2

    # 2. Trigger re-analysis
    new_run = reanalyze_assessment(id=asm1.id, db=db_session)

    # 3. Verify previous assessment run is intact
    db_session.refresh(asm1)
    assert asm1.status == "ANALYZED"
    assert asm1.run_number == 1
    assert asm1.is_stale is True

    # 4. Verify new assessment run
    assert new_run.id != asm1.id
    assert new_run.run_number == 2
    assert new_run.parent_assessment_id == asm1.id
    assert new_run.guideline_version == 2
    assert new_run.application_version == 1
    assert new_run.is_stale is False
    assert new_run.status == "ANALYZED"
