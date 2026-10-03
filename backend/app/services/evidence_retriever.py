import re
from typing import List, Dict, Any
from app.services.parser import ParsedDocument
from app.schemas.ai import RequirementExtracted, EvidenceCandidate

class EvidenceRetriever:
    @staticmethod
    def retrieve_candidates(requirements: List[RequirementExtracted], app_doc: ParsedDocument) -> List[EvidenceCandidate]:
        candidates: List[EvidenceCandidate] = []

        for req in requirements:
            # Extract search keywords from requirement text
            words = [w.lower() for w in re.findall(r'\b[a-zA-Z]{4,}\b', req.text)
                     if w.lower() not in {"must", "shall", "should", "will", "include", "provide", "applicant", "project", "application"}]
            
            matched_chunks: List[str] = []
            matched_pages: List[int] = []
            matched_sections: List[str] = []

            for page in app_doc.pages:
                p_text = page["text"]
                p_num = page["page_number"]
                hits = sum(1 for w in words if w in p_text.lower())
                if hits > 0:
                    matched_chunks.append(p_text[:500])
                    if p_num not in matched_pages:
                        matched_pages.append(p_num)
                    for s in page.get("sections", []):
                        if s not in matched_sections:
                            matched_sections.append(s)

            candidates.append(
                EvidenceCandidate(
                    requirement_id=req.id,
                    relevant_chunks=matched_chunks[:3],
                    pages=matched_pages[:3],
                    sections=matched_sections[:3]
                )
            )

        return candidates
