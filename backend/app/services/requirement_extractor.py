import logging
import re
from typing import List, Optional
from app.services.parser import ParsedDocument, DocumentProcessingError
from app.services.llm_client import BaseLLMClient
from app.schemas.ai import RequirementExtracted, RequirementExtractionResponse

from app.logging import log_event

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
        if not guideline_doc.full_text or len(guideline_doc.full_text.strip()) < 50:
            raise DocumentProcessingError(
                f"We couldn't extract readable text from '{guideline_doc.filename}'. "
                "Please upload a text-based PDF or DOCX."
            )

        log_event(
            event="requirement_extraction_started",
            details={
                "filename": guideline_doc.filename,
                "text_length": len(guideline_doc.full_text),
                "page_count": guideline_doc.page_count,
            },
        )

        prompt = (
            f"Guideline Filename: {guideline_doc.filename}\n"
            f"Page numbers: {'available; total ' + str(guideline_doc.page_count) if guideline_doc.has_physical_page_numbers else 'unavailable for this document format'}\n\n"
            f"Document Text:\n{guideline_doc.full_text[:12000]}"
        )
        res = self.llm.generate_structured(prompt, self.SYSTEM_PROMPT, RequirementExtractionResponse)
        verified_requirements: List[RequirementExtracted] = []

        for requirement in res.requirements:
            source_page_num = self._find_matching_page(requirement.source_excerpt, guideline_doc)
            
            excerpt_found = (source_page_num is not None)
            if not excerpt_found and requirement.source_excerpt:
                norm_excerpt = self._normalize(requirement.source_excerpt)
                norm_full = self._normalize(guideline_doc.full_text)
                if norm_excerpt and norm_excerpt in norm_full:
                    excerpt_found = True
                    source_page_num = 1
                else:
                    excerpt_tokens = set(norm_excerpt.split())
                    full_tokens = set(norm_full.split())
                    if len(excerpt_tokens) >= 4 and len(excerpt_tokens & full_tokens) / len(excerpt_tokens) >= 0.7:
                        excerpt_found = True
                        source_page_num = 1

            if not excerpt_found:
                logger.warning(
                    "Discarding requirement %s because its source excerpt is absent from guideline %s",
                    requirement.id,
                    guideline_doc.filename,
                )
                continue

            source_section = requirement.source_section
            if source_section and self._normalize(source_section) not in self._normalize(guideline_doc.full_text):
                source_section = None

            verified_requirements.append(
                requirement.model_copy(
                    update={
                        "source_document": guideline_doc.filename,
                        "source_page": source_page_num if source_page_num else (1 if guideline_doc.page_count > 0 else None),
                        "source_section": source_section,
                    }
                )
            )

        log_event(
            event="requirement_extraction_completed",
            details={
                "filename": guideline_doc.filename,
                "raw_extracted": len(res.requirements),
                "verified_count": len(verified_requirements),
            },
        )

        return verified_requirements

    def _find_matching_page(self, excerpt: str, guideline_doc: ParsedDocument) -> Optional[int]:
        if not excerpt:
            return None
        norm_excerpt = self._normalize(excerpt)
        if not norm_excerpt:
            return None

        # 1. Exact or normalized substring match in a page
        for page in guideline_doc.pages:
            norm_page = self._normalize(page.get("text", ""))
            if norm_excerpt in norm_page or excerpt.strip().lower() in page.get("text", "").lower():
                return page.get("page_number")

        # 2. Match across full text (e.g. across page boundaries)
        norm_full = self._normalize(guideline_doc.full_text)
        if norm_excerpt in norm_full:
            first_words = " ".join(norm_excerpt.split()[:4])
            for page in guideline_doc.pages:
                if first_words in self._normalize(page.get("text", "")):
                    return page.get("page_number")
            return guideline_doc.pages[0].get("page_number") if guideline_doc.pages else 1

        # 3. High token overlap fallback for LLM-normalized excerpts
        excerpt_tokens = set(norm_excerpt.split())
        if len(excerpt_tokens) >= 4:
            for page in guideline_doc.pages:
                page_tokens = set(self._normalize(page.get("text", "")).split())
                overlap = len(excerpt_tokens & page_tokens) / len(excerpt_tokens)
                if overlap >= 0.75:
                    return page.get("page_number")

        return None

    @staticmethod
    def _normalize(text: str) -> str:
        return " ".join(re.findall(r"\b\w+\b", text.lower()))

