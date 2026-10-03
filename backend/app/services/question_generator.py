from typing import List
from app.services.llm_client import BaseLLMClient
from app.schemas.ai import RequirementExtracted, RequirementMappingItem, ClarificationQuestionItem, ClarificationQuestionResponse

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
        mappings: List[RequirementMappingItem]
    ) -> List[ClarificationQuestionItem]:
        gaps = [m for m in mappings if m.status in ("MISSING", "WEAK", "AMBIGUOUS")]
        if not gaps:
            return []

        gap_summaries = []
        req_map = {r.id: r for r in requirements}
        for g in gaps:
            r = req_map.get(g.requirement_id)
            req_text = r.text if r else ""
            gap_summaries.append(f"Requirement {g.requirement_id} ({g.status}): {req_text} | AI Reasoning: {g.reasoning}")

        prompt = "Gaps identified in application:\n" + "\n".join(gap_summaries)
        res = self.llm.generate_structured(prompt, self.SYSTEM_PROMPT, ClarificationQuestionResponse)
        return res.questions
