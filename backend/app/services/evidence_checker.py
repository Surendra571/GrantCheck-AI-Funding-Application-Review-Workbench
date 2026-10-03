from typing import List
from app.services.parser import ParsedDocument
from app.services.llm_client import BaseLLMClient
from app.schemas.ai import RequirementExtracted, RequirementMappingItem, UnsupportedClaimItem, UnsupportedClaimResponse

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
        for c in res.claims:
            c.status = "No supporting evidence found in supplied materials"
        return res.claims
