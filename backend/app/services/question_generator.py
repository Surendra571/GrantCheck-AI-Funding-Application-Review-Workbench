from typing import List
from app.services.llm_client import BaseLLMClient
from app.schemas.ai import (
    RequirementExtracted,
    RequirementMappingItem,
    UnsupportedClaimItem,
    ClarificationQuestionItem,
    ClarificationQuestionResponse,
)

class QuestionGenerator:
    SYSTEM_PROMPT = (
        "You are a funding application advisor. Generate concise, actionable clarification questions "
        "derived ONLY from identified gaps or ambiguities (MISSING, WEAK, AMBIGUOUS requirements). "
        "Do not formulate questions for fully SUPPORTED requirements."
    )

    def __init__(self, llm_client: BaseLLMClient):
        self.llm = llm_client

    def generate_questions(
        self,
        requirements: List[RequirementExtracted],
        mappings: List[RequirementMappingItem],
        unsupported_claims: List[UnsupportedClaimItem] = None,
    ) -> List[ClarificationQuestionItem]:
        gaps = [m for m in mappings if m.status in ("MISSING", "WEAK", "AMBIGUOUS")]
        claims = unsupported_claims or []
        if not gaps and not claims:
            return []

        gap_summaries = []
        req_map = {r.id: r for r in requirements}
        for g in gaps:
            r = req_map.get(g.requirement_id)
            req_text = r.text if r else ""
            gap_summaries.append(f"Requirement {g.requirement_id} ({g.status}): {req_text} | AI Reasoning: {g.reasoning}")

        claim_summaries = [
            f"Unsupported claim (page {claim.source_page or 'unknown'}, related requirement "
            f"{claim.related_requirement or 'none'}): {claim.claim} | {claim.reason}"
            for claim in claims
        ]
        prompt = "Gaps identified in application:\n" + "\n".join(gap_summaries)
        if claim_summaries:
            prompt += "\n\nUnsupported claims that may need clarification:\n" + "\n".join(claim_summaries)
        res = self.llm.generate_structured(prompt, self.SYSTEM_PROMPT, ClarificationQuestionResponse)

        gap_status_by_id = {mapping.requirement_id: mapping.status for mapping in gaps}
        related_claim_ids = {claim.related_requirement for claim in claims if claim.related_requirement}
        verified_questions = []
        for question in res.questions:
            question_id = question.requirement_id
            if question_id in gap_status_by_id:
                actual_gap = gap_status_by_id[question_id]
                verified_questions.append(question.model_copy(update={"gap_type": actual_gap}))
            elif question_id and question_id not in related_claim_ids:
                continue
            elif not question_id and not claims:
                continue
            else:
                verified_questions.append(question.model_copy(update={"gap_type": "AMBIGUOUS"}))

        return verified_questions
