from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from app.services.parser import DocumentParser
from app.services.citation_verifier import CitationVerifier
from app.services.pipeline_orchestrator import PipelineOrchestrator
from app.services.llm_client import GeminiLLMClient, MockLLMClient, OpenAILLMClient, get_llm_client
from app.services.evidence_checker import EvidenceChecker
from app.schemas.ai import (
    RequirementMappingItem,
    RequirementExtractionResponse,
    UnsupportedClaimItem,
    UnsupportedClaimResponse,
)

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


def test_citation_quote_must_exist_on_the_cited_page():
    first_page = "First page contains general application details only."
    cited_text = "The applicant employs fourteen full-time staff in Manchester."
    doc = DocumentParser.parse(
        (first_page + "\n\n" + " ".join(["padding"] * 410) + "\n\n" + cited_text).encode("utf-8"),
        "multi-page.txt",
    )
    assert doc.page_count == 2
    mapping = RequirementMappingItem(
        requirement_id="REQ-WRONG-PAGE",
        status="SUPPORTED",
        evidence=cited_text,
        source_document="multi-page.txt",
        source_page=1,
        confidence=0.95,
        reasoning="Claimed from page one.",
    )

    verified = CitationVerifier.verify_mappings([mapping], doc)

    assert verified[0].status == "MISSING"
    assert verified[0].evidence is None
    assert "page" in verified[0].reasoning.lower()

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


def test_nonverbatim_quote_with_high_word_overlap_is_rejected():
    doc = DocumentParser.parse(
        b"The applicant has twenty engineers. The project operates in London and aims for growth.",
        "app.txt",
    )
    mapping = RequirementMappingItem(
        requirement_id="REQ-OVERLAP",
        status="SUPPORTED",
        evidence="The applicant operates in London and has twenty engineers in Tokyo.",
        source_document="app.txt",
        source_page=1,
        confidence=0.95,
        reasoning="Most words appear somewhere in the document.",
    )

    verified = CitationVerifier.verify_mappings([mapping], doc)

    assert verified[0].status == "MISSING"
    assert verified[0].evidence is None
    assert "verbatim" in verified[0].reasoning


def test_valid_citation_preserves_supported_mapping():
    doc = DocumentParser.parse(
        b"The company is registered in the United Kingdom and employs twelve staff.",
        "app.txt",
    )
    mapping = RequirementMappingItem(
        requirement_id="REQ-VALID",
        status="SUPPORTED",
        evidence="The company is registered in the United Kingdom and employs twelve staff.",
        source_document="app.txt",
        source_page=1,
        confidence=0.95,
        reasoning="Directly supported by the application.",
    )

    verified = CitationVerifier.verify_mappings([mapping], doc)

    assert verified[0].status == "SUPPORTED"
    assert verified[0].evidence == mapping.evidence
    assert verified[0].source_page == 1


def test_ambiguous_mapping_stays_ambiguous_when_quote_is_verifiable():
    doc = DocumentParser.parse(b"The project expects a 30 to 40 percent reduction.", "app.txt")
    mapping = RequirementMappingItem(
        requirement_id="REQ-AMBIGUOUS",
        status="AMBIGUOUS",
        evidence="The project expects a 30 to 40 percent reduction.",
        source_document="app.txt",
        source_page=1,
        confidence=0.6,
        reasoning="The range does not establish a single verified outcome.",
    )

    verified = CitationVerifier.verify_mappings([mapping], doc)

    assert verified[0].status == "AMBIGUOUS"
    assert verified[0].evidence == mapping.evidence

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


@pytest.mark.parametrize("evidence", [None, "   "])
def test_supported_mapping_without_evidence_is_downgraded(evidence):
    doc = DocumentParser.parse(b"The application contains project details.", "app.txt")
    mapping = RequirementMappingItem(
        requirement_id="REQ-4",
        status="SUPPORTED",
        evidence=evidence,
        source_document="app.txt",
        confidence=0.99,
        reasoning="Claimed as complete without a citation.",
    )

    verified = CitationVerifier.verify_mappings([mapping], doc)

    assert verified[0].status == "MISSING"
    assert verified[0].evidence is None
    assert verified[0].confidence == 0.0
    assert "no verifiable evidence" in verified[0].reasoning.lower()

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


def test_unsupported_claims_require_source_text_and_correct_page():
    page_one = "The organization was established in the region."
    real_claim = "Our pilot reduced water consumption by 28 percent."
    application = DocumentParser.parse(
        (page_one + "\n\n" + " ".join(["padding"] * 410) + "\n\n" + real_claim).encode("utf-8"),
        "application.txt",
    )

    class ClaimClient:
        def generate_structured(self, prompt, system_prompt, schema):
            return UnsupportedClaimResponse(
                claims=[
                    UnsupportedClaimItem(
                        claim="Our facility uses zero energy worldwide.",
                        source_page=1,
                        reason="No evidence was supplied.",
                    ),
                    UnsupportedClaimItem(
                        claim=real_claim,
                        source_page=1,
                        reason="No independent test report was supplied.",
                    ),
                ]
            )

    claims = EvidenceChecker(ClaimClient()).check_claims(application, [], [])

    assert len(claims) == 1
    assert claims[0].claim == real_claim
    assert claims[0].source_page == 2
    assert claims[0].status == "No supporting evidence found in supplied materials"

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

def test_openai_null_structured_response_retries_then_fails(monkeypatch, caplog):
    client = OpenAILLMClient.__new__(OpenAILLMClient)
    client.client = MagicMock()
    client.model = "test-model"
    client.client.beta.chat.completions.parse.return_value = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(parsed=None))]
    )
    monkeypatch.setattr("app.services.llm_client.settings.LLM_MAX_RETRIES", 2)
    monkeypatch.setattr("app.services.llm_client.time.sleep", lambda _delay: None)

    with pytest.raises(RuntimeError, match="OpenAI LLM failure after 2 attempts"):
        client.generate_structured("prompt", "system", RequirementExtractionResponse)

    assert client.client.beta.chat.completions.parse.call_count == 2


def test_openai_exception_text_is_not_logged_or_raised(monkeypatch, caplog):
    client = OpenAILLMClient.__new__(OpenAILLMClient)
    client.client = MagicMock()
    client.model = "test-model"
    client.client.beta.chat.completions.parse.side_effect = ValueError("credential-sentinel-openai")
    monkeypatch.setattr("app.services.llm_client.settings.LLM_MAX_RETRIES", 1)
    monkeypatch.setattr("app.services.llm_client.time.sleep", lambda _delay: None)

    with pytest.raises(RuntimeError) as exc:
        client.generate_structured("prompt", "system", RequirementExtractionResponse)

    assert "credential-sentinel-openai" not in caplog.text
    assert "credential-sentinel-openai" not in str(exc.value)


def test_gemini_exception_text_is_not_logged_or_raised(monkeypatch, caplog):
    client = GeminiLLMClient.__new__(GeminiLLMClient)
    client.model = MagicMock()
    client.model.generate_content.side_effect = ValueError("credential-sentinel-gemini")
    monkeypatch.setattr("app.services.llm_client.settings.LLM_MAX_RETRIES", 2)
    monkeypatch.setattr("app.services.llm_client.time.sleep", lambda _delay: None)

    with pytest.raises(RuntimeError, match="Gemini LLM failure after 2 attempts") as exc:
        client.generate_structured("prompt", "system", RequirementExtractionResponse)

    assert client.model.generate_content.call_count == 2
    assert "credential-sentinel-gemini" not in caplog.text
    assert "credential-sentinel-gemini" not in str(exc.value)


def test_gemini_malformed_json_retries_then_fails(monkeypatch):
    client = GeminiLLMClient.__new__(GeminiLLMClient)
    client.model = MagicMock()
    client.model.generate_content.return_value = SimpleNamespace(text="{not valid json")
    monkeypatch.setattr("app.services.llm_client.settings.LLM_MAX_RETRIES", 2)
    monkeypatch.setattr("app.services.llm_client.time.sleep", lambda _delay: None)

    with pytest.raises(RuntimeError, match="Gemini LLM failure after 2 attempts"):
        client.generate_structured("prompt", "system", RequirementExtractionResponse)

    assert client.model.generate_content.call_count == 2


@pytest.mark.parametrize(
    ("provider", "key_name"),
    [("openai", "OPENAI_API_KEY"), ("gemini", "GEMINI_API_KEY")],
)
def test_selected_provider_without_api_key_fails_instead_of_falling_back(
    monkeypatch, provider, key_name
):
    monkeypatch.setattr("app.services.llm_client.settings.LLM_PROVIDER", provider)
    monkeypatch.setattr("app.services.llm_client.settings.OPENAI_API_KEY", "")
    monkeypatch.setattr("app.services.llm_client.settings.GEMINI_API_KEY", "")

    with pytest.raises(RuntimeError, match=f"{key_name} to be configured"):
        get_llm_client()
