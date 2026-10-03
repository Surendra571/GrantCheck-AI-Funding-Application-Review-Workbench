from typing import List
from app.services.parser import ParsedDocument
from app.services.llm_client import BaseLLMClient
from app.schemas.ai import RequirementExtracted, RequirementExtractionResponse

class RequirementExtractor:
    SYSTEM_PROMPT = (
        "You are an expert grant review system. Extract structured requirements from the provided grant guideline document. "
        "Classify each requirement as 'mandatory', 'recommendation', 'eligibility-related', or 'submission-related'. "
        "Assign categories: 'eligibility', 'submission', 'documentation', 'project', 'financial', 'organisation', 'recommendation', or 'other'. "
        "Include source document, page, section, and exact excerpt citation. Do not invent requirements."
    )

    def __init__(self, llm_client: BaseLLMClient):
        self.llm = llm_client

    def extract(self, guideline_doc: ParsedDocument) -> List[RequirementExtracted]:
        prompt = (
            f"Guideline Filename: {guideline_doc.filename}\n"
            f"Total Pages: {guideline_doc.page_count}\n\n"
            f"Document Text:\n{guideline_doc.full_text[:12000]}"
        )
        res = self.llm.generate_structured(prompt, self.SYSTEM_PROMPT, RequirementExtractionResponse)
        return res.requirements
