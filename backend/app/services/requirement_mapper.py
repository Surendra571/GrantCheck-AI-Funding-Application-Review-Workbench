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

        candidate_by_id = {candidate.requirement_id: candidate for candidate in (candidates or [])}
        candidate_summaries = []
        for requirement in requirements:
            candidate = candidate_by_id.get(requirement.id)
            if candidate and candidate.relevant_chunks:
                candidate_summaries.append(
                    f"[{requirement.id}] Pages {candidate.pages}; sections {candidate.sections}:\n"
                    + "\n---\n".join(candidate.relevant_chunks)
                )
            else:
                candidate_summaries.append(f"[{requirement.id}] No relevant text candidates were retrieved.")

        prompt = (
            f"Requirements to map:\n" + "\n".join(req_summaries) + "\n\n"
            f"Retrieved evidence candidates:\n" + "\n\n".join(candidate_summaries) + "\n\n"
            f"Application Filename: {application_doc.filename}\n"
            f"Total Pages: {application_doc.page_count}\n\n"
            f"Application Content:\n{application_doc.full_text[:14000]}"
        )

        res = self.llm.generate_structured(prompt, self.SYSTEM_PROMPT, RequirementMappingResponse)
        mappings_by_id = {}
        requirement_ids = {requirement.id for requirement in requirements}
        for mapping in res.mappings:
            if mapping.requirement_id in requirement_ids and mapping.requirement_id not in mappings_by_id:
                mappings_by_id[mapping.requirement_id] = mapping

        return [
            mappings_by_id.get(
                requirement.id,
                RequirementMappingItem(
                    requirement_id=requirement.id,
                    status="MISSING",
                    evidence=None,
                    source_document=application_doc.filename,
                    confidence=0.0,
                    reasoning="No evidence mapping was returned for this requirement; treated as missing.",
                ),
            )
            for requirement in requirements
        ]
