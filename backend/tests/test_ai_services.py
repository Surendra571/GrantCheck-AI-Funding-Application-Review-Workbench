import os
import pytest
from app.services.parser import DocumentParser
from app.services.llm_client import MockLLMClient
from app.services.requirement_extractor import RequirementExtractor
from app.services.requirement_mapper import RequirementMapper
from app.services.evidence_checker import EvidenceChecker
from app.services.question_generator import QuestionGenerator
from app.schemas.ai import ClarificationQuestionItem, ClarificationQuestionResponse, RequirementMappingResponse, UnsupportedClaimItem

SAMPLES_DIR = os.path.join(os.path.dirname(__file__), "..", "app", "samples")


def load_sample(name):
    with open(os.path.join(SAMPLES_DIR, name), "rb") as sample_file:
        return sample_file.read()

def test_requirement_extractor():
    llm = MockLLMClient()
    extractor = RequirementExtractor(llm)
    doc = DocumentParser.parse(load_sample("sample_guideline.md"), "sample_guideline.md")
    reqs = extractor.extract(doc)

    assert len(reqs) >= 3
    assert any(r.mandatory for r in reqs)
    assert any(not r.mandatory for r in reqs)
    for r in reqs:
        assert r.category in ("eligibility", "financial", "project", "recommendation", "submission", "documentation", "organisation", "other")


def test_requirement_extractor_does_not_invent_unrelated_requirements():
    guideline_text = (
        "The programme funds community arts projects. Applicants submit a portfolio and a short budget."
    )
    document = DocumentParser.parse(guideline_text.encode("utf-8"), "arts-guideline.txt")

    requirements = RequirementExtractor(MockLLMClient()).extract(document)

    normalized_guideline = " ".join(guideline_text.lower().split())
    assert all(
        " ".join(requirement.source_excerpt.lower().split()) in normalized_guideline
        for requirement in requirements
    )

def test_requirement_mapper():
    llm = MockLLMClient()
    extractor = RequirementExtractor(llm)
    mapper = RequirementMapper(llm)

    g_doc = DocumentParser.parse(load_sample("sample_guideline.md"), "sample_guideline.md")
    a_doc = DocumentParser.parse(load_sample("sample_application.md"), "sample_application.md")

    reqs = extractor.extract(g_doc)
    mappings = mapper.map_requirements(reqs, a_doc)

    assert len(mappings) >= 3
    statuses = {m.status for m in mappings}
    assert "SUPPORTED" in statuses
    assert "MISSING" in statuses


def test_requirement_mapper_marks_omitted_llm_mapping_missing():
    class OmitMappingsClient:
        def generate_structured(self, prompt, system_prompt, schema):
            assert "Retrieved evidence candidates" in prompt
            return RequirementMappingResponse(mappings=[])

    document = DocumentParser.parse(load_sample("sample_guideline.md"), "sample_guideline.md")
    requirements = RequirementExtractor(MockLLMClient()).extract(document)
    application = DocumentParser.parse(load_sample("sample_application.md"), "sample_application.md")

    mappings = RequirementMapper(OmitMappingsClient()).map_requirements(requirements, application)

    assert len(mappings) == len(requirements)
    assert {mapping.requirement_id for mapping in mappings} == {requirement.id for requirement in requirements}
    assert all(mapping.status == "MISSING" for mapping in mappings)
    assert all(mapping.evidence is None for mapping in mappings)

def test_evidence_checker_does_not_declare_claim_false():
    llm = MockLLMClient()
    checker = EvidenceChecker(llm)
    a_doc = DocumentParser.parse(load_sample("sample_application.md"), "sample_application.md")

    claims = checker.check_claims(a_doc, [], [])
    assert len(claims) > 0
    for c in claims:
        # Crucial requirement: never declare false
        assert "false" not in c.status.lower()
        assert "No supporting evidence found in supplied materials" in c.status

def test_question_generator():
    llm = MockLLMClient()
    extractor = RequirementExtractor(llm)
    mapper = RequirementMapper(llm)
    q_gen = QuestionGenerator(llm)

    g_doc = DocumentParser.parse(load_sample("sample_guideline.md"), "sample_guideline.md")
    a_doc = DocumentParser.parse(load_sample("sample_application.md"), "sample_application.md")

    reqs = extractor.extract(g_doc)
    mappings = mapper.map_requirements(reqs, a_doc)
    questions = q_gen.generate_questions(reqs, mappings)

    assert len(questions) > 0
    for q in questions:
        assert q.gap_type in ("MISSING", "WEAK", "AMBIGUOUS")
        assert len(q.question) > 5


def test_question_generator_uses_unsupported_claims_when_no_requirement_gap_exists():
    claim_text = "Our membrane technology reduces filtration energy consumption by 65%."

    class ClaimQuestionClient:
        def generate_structured(self, prompt, system_prompt, schema):
            assert claim_text in prompt
            return ClarificationQuestionResponse(
                questions=[
                    ClarificationQuestionItem(
                        question="Can you provide independent test data supporting the 65% reduction?",
                        gap_type="AMBIGUOUS",
                        suggested_evidence="A third-party comparative energy test report.",
                    )
                ]
            )

    claim = UnsupportedClaimItem(claim=claim_text, reason="No independent test report was supplied.")
    questions = QuestionGenerator(ClaimQuestionClient()).generate_questions([], [], [claim])

    assert len(questions) == 1
    assert questions[0].requirement_id is None
    assert questions[0].gap_type == "AMBIGUOUS"
    assert "independent test data" in questions[0].question
