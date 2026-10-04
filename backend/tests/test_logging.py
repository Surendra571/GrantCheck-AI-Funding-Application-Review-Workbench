import logging
import json
from app.logging import log_event, sanitize_data

def test_sanitize_data_strips_sensitive_keys():
    raw = {
        "user": "reviewer",
        "api_key": "sk-secret123456",
        "password": "supersecretpassword",
        "auth_token": "bearer xyz",
        "details": {
            "secret_number": 999,
            "filename": "application.pdf"
        }
    }
    sanitized = sanitize_data(raw)
    assert sanitized["user"] == "reviewer"
    assert sanitized["api_key"] == "[REDACTED]"
    assert sanitized["password"] == "[REDACTED]"
    assert sanitized["auth_token"] == "[REDACTED]"
    assert sanitized["details"]["secret_number"] == "[REDACTED]"
    assert sanitized["details"]["filename"] == "application.pdf"

def test_log_event_emits_structured_json(caplog):
    with caplog.at_level(logging.INFO):
        log_event(
            event="requirement_extraction_completed",
            assessment_id="test-asm-123",
            document_id="doc-456",
            operation="extract_requirements",
            status="success",
            duration_ms=45.2,
            details={"count": 5, "api_key": "leak-prevention"}
        )

    assert len(caplog.records) >= 1
    msg = caplog.records[-1].message
    assert "[requirement_extraction_completed]" in msg
    assert '"event": "requirement_extraction_completed"' in msg
    assert '"assessment_id": "test-asm-123"' in msg
    assert '"document_id": "doc-456"' in msg
    assert '"duration_ms": 45.2' in msg
    assert '"api_key": "[REDACTED]"' in msg
    assert "leak-prevention" not in msg

def test_all_twelve_core_structured_events_callable(caplog):
    events = [
        "assessment_created",
        "document_uploaded",
        "document_parsed",
        "requirement_extraction_started",
        "requirement_extraction_completed",
        "mapping_started",
        "mapping_completed",
        "review_confirmed",
        "review_corrected",
        "review_rejected",
        "assessment_marked_stale",
        "analysis_failed",
    ]
    with caplog.at_level(logging.INFO):
        for ev in events:
            log_event(event=ev, assessment_id="asm-id", operation=ev, details={"step": ev})

    captured_text = caplog.text
    for ev in events:
        assert f"[{ev}]" in captured_text

