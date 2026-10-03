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
        logger.info(f"Step 1: Parsing guideline '{guideline_filename}'...")
        guideline_doc: ParsedDocument = DocumentParser.parse(guideline_bytes, guideline_filename)

        # Step 2: Extract Requirements
        logger.info("Step 2: Extracting structured requirements...")
        requirements = self.extractor.extract(guideline_doc)

        # Step 3: Parse Application
        logger.info(f"Step 3: Parsing application '{application_filename}'...")
        application_doc: ParsedDocument = DocumentParser.parse(application_bytes, application_filename)

        # Step 4: Retrieve Relevant Application Evidence
        logger.info("Step 4: Retrieving evidence candidates...")
        candidates = EvidenceRetriever.retrieve_candidates(requirements, application_doc)

        # Step 5: Map Evidence to Requirements
        logger.info("Step 5: Mapping evidence to requirements...")
        raw_mappings = self.mapper.map_requirements(requirements, application_doc, candidates)

        # Step 6: Anti-Hallucination Citation Verification
        logger.info("Step 6: Verifying citations and detecting weak/missing evidence...")
        verified_mappings = CitationVerifier.verify_mappings(raw_mappings, application_doc)

        # Step 7: Detect Unsupported Claims
        logger.info("Step 7: Detecting unsupported claims...")
        unsupported_claims = self.checker.check_claims(application_doc, requirements, verified_mappings)

        # Step 8: Generate Clarification Questions
        logger.info("Step 8: Generating clarification questions...")
        clarification_questions = self.question_gen.generate_questions(requirements, verified_mappings)

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
