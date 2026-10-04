import logging
from typing import Dict, Any
from app.services.parser import DocumentParser, ParsedDocument
from app.services.llm_client import BaseLLMClient
from app.services.evidence_retriever import EvidenceRetriever
from app.services.citation_verifier import CitationVerifier
from app.services.requirement_extractor import RequirementExtractor
from app.services.requirement_mapper import RequirementMapper
from app.services.evidence_checker import EvidenceChecker
from app.services.question_generator import QuestionGenerator
from app.schemas.ai import PipelineAuditSnapshot

from app.logging import log_event

logger = logging.getLogger(__name__)

class PipelineOrchestrator:
    def __init__(self, llm_client: BaseLLMClient):
        self.llm = llm_client
        self.extractor = RequirementExtractor(llm_client)
        self.mapper = RequirementMapper(llm_client)
        self.checker = EvidenceChecker(llm_client)
        self.question_gen = QuestionGenerator(llm_client)

    def run_pipeline(
        self,
        guideline_bytes: bytes,
        guideline_filename: str,
        application_bytes: bytes,
        application_filename: str
    ) -> Dict[str, Any]:
        # Step 1: Parse Guideline
        guideline_doc: ParsedDocument = DocumentParser.parse(guideline_bytes, guideline_filename)
        log_event(
            event="document_parsed",
            details={"doc_type": "guideline", "filename": guideline_filename, "pages": guideline_doc.page_count},
        )
        log_event(
            event="text_extracted",
            details={"doc_type": "guideline", "filename": guideline_filename, "char_count": len(guideline_doc.full_text)},
        )

        # Step 2: Extract Requirements
        requirements = self.extractor.extract(guideline_doc)

        # Step 3: Parse Application
        application_doc: ParsedDocument = DocumentParser.parse(application_bytes, application_filename)
        log_event(
            event="document_parsed",
            details={"doc_type": "application", "filename": application_filename, "pages": application_doc.page_count},
        )
        log_event(
            event="text_extracted",
            details={"doc_type": "application", "filename": application_filename, "char_count": len(application_doc.full_text)},
        )

        # Step 4: Retrieve Relevant Application Evidence
        candidates = EvidenceRetriever.retrieve_candidates(requirements, application_doc)

        # Step 5: Map Evidence to Requirements
        log_event(
            event="mapping_started",
            details={"requirement_count": len(requirements)},
        )
        raw_mappings = self.mapper.map_requirements(requirements, application_doc, candidates)

        # Step 6: Anti-Hallucination Citation Verification
        verified_mappings = CitationVerifier.verify_mappings(raw_mappings, application_doc)
        supported_count = sum(1 for m in verified_mappings if m.status == "SUPPORTED")
        weak_count = sum(1 for m in verified_mappings if m.status in ("WEAK", "AMBIGUOUS"))
        missing_count = sum(1 for m in verified_mappings if m.status == "MISSING")
        log_event(
            event="mapping_completed",
            details={
                "total_mappings": len(verified_mappings),
                "supported": supported_count,
                "weak": weak_count,
                "missing": missing_count,
            },
        )

        # Step 7: Detect Unsupported Claims
        unsupported_claims = self.checker.check_claims(application_doc, requirements, verified_mappings)
        log_event(
            event="unsupported_claims_detected",
            details={"unsupported_count": len(unsupported_claims)},
        )

        # Step 8: Generate Clarification Questions
        clarification_questions = self.question_gen.generate_questions(
            requirements,
            verified_mappings,
            unsupported_claims,
        )
        log_event(
            event="questions_generated",
            details={"question_count": len(clarification_questions)},
        )

        # Construct full audit snapshot
        snapshot = PipelineAuditSnapshot(
            guideline_filename=guideline_filename,
            application_filename=application_filename,
            guideline_pages=guideline_doc.page_count,
            application_pages=application_doc.page_count,
            extracted_requirements=requirements,
            mappings=verified_mappings,
            unsupported_claims=unsupported_claims,
            clarification_questions=clarification_questions
        )

        return {
            "guideline_doc": guideline_doc,
            "application_doc": application_doc,
            "requirements": requirements,
            "mappings": verified_mappings,
            "unsupported_claims": unsupported_claims,
            "clarification_questions": clarification_questions,
            "audit_snapshot": snapshot.model_dump()
        }
