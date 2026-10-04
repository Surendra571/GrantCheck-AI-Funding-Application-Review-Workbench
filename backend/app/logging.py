import json
import logging
from typing import Any, Optional

logger = logging.getLogger("grantcheck")

# Configure root logger format if not already configured
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

SENSITIVE_KEYS = {"key", "token", "password", "secret", "auth", "authorization", "bearer", "cookie"}

def sanitize_data(data: Any) -> Any:
    """Recursively strip any sensitive keys like tokens, keys, passwords."""
    if isinstance(data, dict):
        cleaned = {}
        for k, v in data.items():
            if any(s in str(k).lower() for s in SENSITIVE_KEYS):
                cleaned[k] = "[REDACTED]"
            else:
                cleaned[k] = sanitize_data(v)
        return cleaned
    elif isinstance(data, list):
        return [sanitize_data(item) for item in data]
    return data

def log_event(
    event: str,
    assessment_id: Optional[str] = None,
    document_id: Optional[str] = None,
    operation: Optional[str] = None,
    status: Optional[str] = "success",
    duration_ms: Optional[float] = None,
    details: Optional[dict] = None,
    level: int = logging.INFO,
):
    """
    Emits structured, audit-ready log records for core workflow events.
    Never logs sensitive keys, credentials, or oversized document bodies.
    """
    payload = {
        "event": event,
        "operation": operation or event,
        "status": status,
    }
    if assessment_id:
        payload["assessment_id"] = assessment_id
    if document_id:
        payload["document_id"] = document_id
    if duration_ms is not None:
        payload["duration_ms"] = round(duration_ms, 2)
    if details:
        payload["details"] = sanitize_data(details)

    logger.log(level, f"[{event}] {json.dumps(payload)}")

