import logging
import re
from typing import List
from app.services.parser import ParsedDocument
from app.services.llm_client import BaseLLMClient
from app.schemas.ai import RequirementExtracted, RequirementMappingItem, UnsupportedClaimItem, UnsupportedClaimResponse

logger = logging.getLogger(__name__)

class EvidenceChecker:
    SYSTEM_PROMPT = (
        "You are an evidence verification specialist. Identify substantive claims made in the draft application "
        "for which no verifiable evidence or documentation was supplied. "
        "CRITICAL RULE: Do NOT declare any claim false. "
        "State strictly that: 'No supporting evidence found in supplied materials'."
    )

    def __init__(self, llm_client: BaseLLMClient):
        self.llm = llm_client

    def check_claims(
        self,
        application_doc: ParsedDocument,
        requirements: List[RequirementExtracted],
        mappings: List[RequirementMappingItem]
    ) -> List[UnsupportedClaimItem]:
        prompt = (
            f"Analyze application document '{application_doc.filename}' for unsupported substantive claims:\n"
            f"{application_doc.full_text[:12000]}"
        )
        res = self.llm.generate_structured(prompt, self.SYSTEM_PROMPT, UnsupportedClaimResponse)
        normalized_pages = {
            page["page_number"]: " ".join(re.findall(r"\b\w+\b", page["text"].lower()))
            for page in application_doc.pages
        }
        verified_claims = []
        for c in res.claims:
            normalized_claim = " ".join(re.findall(r"\b\w+\b", c.claim.lower()))
            matching_pages = [
                page_number
                for page_number, page_text in normalized_pages.items()
                if normalized_claim and normalized_claim in page_text
            ]
            if not matching_pages:
                logger.warning(
                    "Discarding unsupported claim because its text is absent from application %s",
                    application_doc.filename,
                )
                continue

            if c.source_page not in matching_pages:
                c.source_page = matching_pages[0]
            c.status = "No supporting evidence found in supplied materials"
            verified_claims.append(c)
        return verified_claims
