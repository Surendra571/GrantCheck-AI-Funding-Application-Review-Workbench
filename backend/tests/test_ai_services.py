import pytest
from app.services.parser import DocumentParser
from app.services.llm_client import MockLLMClient
from app.services.requirement_extractor import RequirementExtractor
from app.services.requirement_mapper import RequirementMapper
from app.services.evidence_checker import EvidenceChecker
from app.services.question_generator import QuestionGenerator

def test_requirement_extractor():
    llm = MockLLMClient()
    extractor = RequirementExtractor(llm)
    doc = DocumentParser.parse(b"Guideline test text", "guideline.txt")
    reqs = extractor.extract(doc)

    assert len(reqs) >= 3
    assert any(r.mandatory for r in reqs)
    assert any(not r.mandatory for r in reqs)
    for r in reqs:
        assert r.category in ("eligibility", "financial", "project", "recommendation", "submission", "documentation", "organisation", "other")

def test_requirement_mapper():
    llm = MockLLMClient()
    extractor = RequirementExtractor(llm)
    mapper = RequirementMapper(llm)

    g_doc = DocumentParser.parse(b"Guideline text", "guideline.txt")
    a_doc = DocumentParser.parse(b"Application text", "application.txt")

    reqs = extractor.extract(g_doc)
    mappings = mapper.map_requirements(reqs, a_doc)

    assert len(mappings) >= 3
    statuses = {m.status for m in mappings}
    assert "SUPPORTED" in statuses
    assert "MISSING" in statuses

def test_evidence_checker_does_not_declare_claim_false():
    llm = MockLLMClient()
    checker = EvidenceChecker(llm)
    a_doc = DocumentParser.parse(b"Application text with claims", "application.txt")

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

    g_doc = DocumentParser.parse(b"Guideline text", "guideline.txt")
    a_doc = DocumentParser.parse(b"Application text", "application.txt")

    reqs = extractor.extract(g_doc)
    mappings = mapper.map_requirements(reqs, a_doc)
    questions = q_gen.generate_questions(reqs, mappings)

    assert len(questions) > 0
    for q in questions:
        assert q.gap_type in ("MISSING", "WEAK", "AMBIGUOUS")
        assert len(q.question) > 5
