import logging
import re
from typing import List
from app.services.parser import ParsedDocument
from app.services.llm_client import BaseLLMClient
from app.schemas.ai import RequirementExtracted, RequirementExtractionResponse

logger = logging.getLogger(__name__)

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
            f"Page numbers: {'available; total ' + str(guideline_doc.page_count) if guideline_doc.has_physical_page_numbers else 'unavailable for this document format'}\n\n"
            f"Document Text:\n{guideline_doc.full_text[:12000]}"
        )
        res = self.llm.generate_structured(prompt, self.SYSTEM_PROMPT, RequirementExtractionResponse)
        verified_requirements: List[RequirementExtracted] = []
        for requirement in res.requirements:
            excerpt = self._normalize(requirement.source_excerpt)
            matching_pages = [
                page
                for page in guideline_doc.pages
                if excerpt and excerpt in self._normalize(page["text"])
            ] if guideline_doc.has_physical_page_numbers else []
            excerpt_found = bool(matching_pages) if guideline_doc.has_physical_page_numbers else (
                bool(excerpt) and excerpt in self._normalize(guideline_doc.full_text)
            )
            if not excerpt_found:
                logger.warning(
                    "Discarding requirement %s because its source excerpt is absent from guideline %s",
                    requirement.id,
                    guideline_doc.filename,
                )
                continue

            source_page = matching_pages[0] if matching_pages else None
            source_section = requirement.source_section
            if source_section and self._normalize(source_section) not in self._normalize(guideline_doc.full_text):
                source_section = None

            verified_requirements.append(
                requirement.model_copy(
                    update={
                        "source_document": guideline_doc.filename,
                        "source_page": source_page["page_number"] if source_page else None,
                        "source_section": source_section,
                    }
                )
            )

        return verified_requirements

    @staticmethod
    def _normalize(text: str) -> str:
        return " ".join(re.findall(r"\b\w+\b", text.lower()))
