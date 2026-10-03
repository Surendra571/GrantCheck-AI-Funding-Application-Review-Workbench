from typing import List
from app.services.parser import ParsedDocument
from app.services.llm_client import BaseLLMClient
from app.schemas.ai import RequirementExtracted, RequirementMappingItem, RequirementMappingResponse, EvidenceCandidate

class RequirementMapper:
    SYSTEM_PROMPT = (
        "You are an expert grant compliance reviewer. Map each requirement to evidence in the draft application. "
        "Status must be strictly one of: SUPPORTED, WEAK, MISSING, AMBIGUOUS. "
        "Provide exact citations (document, page, section, quoted evidence). "
        "If evidence cannot be found, return MISSING instead of guessing. "
        "Never invent requirements, evidence, page numbers, or facts."
    )

    def __init__(self, llm_client: BaseLLMClient):
        self.llm = llm_client

    def map_requirements(
        self,
        requirements: List[RequirementExtracted],
        application_doc: ParsedDocument,
        candidates: List[EvidenceCandidate] = None
    ) -> List[RequirementMappingItem]:
        req_summaries = []
        for r in requirements:
            req_summaries.append(f"[{r.id}] ({r.type}, {r.category}): {r.text}")

        prompt = (
            f"Requirements to map:\n" + "\n".join(req_summaries) + "\n\n"
            f"Application Filename: {application_doc.filename}\n"
            f"Total Pages: {application_doc.page_count}\n\n"
            f"Application Content:\n{application_doc.full_text[:14000]}"
        )

        res = self.llm.generate_structured(prompt, self.SYSTEM_PROMPT, RequirementMappingResponse)
        return res.mappings
