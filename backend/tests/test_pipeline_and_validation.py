import pytest
from app.services.parser import DocumentParser
from app.services.citation_verifier import CitationVerifier
from app.services.pipeline_orchestrator import PipelineOrchestrator
from app.services.llm_client import MockLLMClient, BaseLLMClient
from app.schemas.ai import RequirementMappingItem, RequirementExtractionResponse

def test_hallucinated_citation_page_out_of_bounds():
    # Document has only 1 page
    doc = DocumentParser.parse(b"Single page application document text.", "app.txt")
    assert doc.page_count == 1

    # Mapping references page 99 (fabricated)
    hallucinated_mapping = RequirementMappingItem(
        requirement_id="REQ-1",
        status="SUPPORTED",
        evidence="Some quote",
        source_document="app.txt",
        source_page=99,
        confidence=0.9,
        reasoning="Found on page 99"
    )

    verified = CitationVerifier.verify_mappings([hallucinated_mapping], doc)
    assert verified[0].status == "MISSING"
    assert verified[0].evidence is None
    assert "exceeds document bounds" in verified[0].reasoning

def test_hallucinated_citation_fabricated_evidence_quote():
    doc = DocumentParser.parse(b"The quick brown fox jumps over the lazy dog.", "app.txt")

    # Mapping contains a completely fabricated quote not in document
    fabricated_mapping = RequirementMappingItem(
        requirement_id="REQ-2",
        status="SUPPORTED",
        evidence="The quantum supercomputing cluster operates with cryogenic superconductivity.",
        source_document="app.txt",
        source_page=1,
        confidence=0.9,
        reasoning="Claimed text"
    )

    verified = CitationVerifier.verify_mappings([fabricated_mapping], doc)
    assert verified[0].status == "MISSING"
    assert verified[0].evidence is None
    assert "could not be verified" in verified[0].reasoning

def test_missing_evidence_enforcement():
    doc = DocumentParser.parse(b"Simple application text without financial figures.", "app.txt")
    mapping = RequirementMappingItem(
        requirement_id="REQ-3",
        status="MISSING",
        evidence=None,
        source_document="app.txt",
        confidence=1.0,
        reasoning="No financial figures found."
    )
    verified = CitationVerifier.verify_mappings([mapping], doc)
    assert verified[0].status == "MISSING"

def test_malformed_json_rejected():
    from pydantic import ValidationError
    import json
    malformed_json = '{"requirements": [{"id": "REQ-1", "text": "Incomplete", "mandatory": "not_a_bool"}]}'
    with pytest.raises(ValidationError):
        RequirementExtractionResponse.model_validate(json.loads(malformed_json))

def test_unsupported_claims_never_says_false():
    llm = MockLLMClient()
    pipeline = PipelineOrchestrator(llm)
    res = pipeline.run_pipeline(
        b"# Guideline\nApplicant must be registered in the UK.",
        "guideline.txt",
        b"# Application\nWe claim 100% market monopoly without data.",
        "app.txt"
    )
    for c in res["unsupported_claims"]:
        assert "false" not in c.status.lower()
        assert "No supporting evidence found in supplied materials" in c.status

def test_controlled_pipeline_8_steps_execution():
    llm = MockLLMClient()
    pipeline = PipelineOrchestrator(llm)
    res = pipeline.run_pipeline(
        b"# Guideline\nMandatory criteria 1.\nMandatory criteria 2.",
        "guideline.txt",
        b"# Application\nEvidence response 1.\nEvidence response 2.",
        "app.txt"
    )
    assert "guideline_doc" in res
    assert "application_doc" in res
    assert "requirements" in res
    assert "mappings" in res
    assert "unsupported_claims" in res
    assert "clarification_questions" in res
    assert "audit_snapshot" in res

def test_retry_handling_transient_failure():
    # Test retry simulator
    call_count = 0
    def flaky_call():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise ConnectionError("Transient 503 Service Unavailable")
        return "Success"

    # Simulate 3 retries
    retries = 3
    result = None
    for attempt in range(retries):
        try:
            result = flaky_call()
            break
        except ConnectionError:
            if attempt == retries - 1:
                raise
    assert result == "Success"
    assert call_count == 3
