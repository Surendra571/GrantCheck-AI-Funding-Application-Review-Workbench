import re
from typing import List
from app.services.parser import ParsedDocument
from app.schemas.ai import RequirementMappingItem

class CitationVerifier:
    """Anti-hallucination layer ensuring citations and quoted evidence strictly exist in supplied documents."""

    @staticmethod
    def verify_mappings(mappings: List[RequirementMappingItem], app_doc: ParsedDocument) -> List[RequirementMappingItem]:
        verified_mappings: List[RequirementMappingItem] = []
        normalize = lambda value: " ".join(re.findall(r"\b\w+\b", value.lower()))
        normalized_pages = {
            page["page_number"]: normalize(page["text"])
            for page in app_doc.pages
        }

        for m in mappings:
            if m.status != "MISSING" and not (m.evidence and m.evidence.strip()):
                verified_mappings.append(
                    RequirementMappingItem(
                        requirement_id=m.requirement_id,
                        status="MISSING",
                        evidence=None,
                        source_document=app_doc.filename,
                        source_page=None,
                        source_section=None,
                        confidence=0.0,
                        reasoning=(
                            f"Overridden to MISSING: no verifiable evidence excerpt was supplied for {m.status} status."
                        ),
                    )
                )
                continue

            # 1. Verify Page Out-of-Bounds
            if m.source_page is not None:
                if m.source_page < 1 or m.source_page > app_doc.page_count:
                    # Fabricated page number detected
                    verified_mappings.append(
                        RequirementMappingItem(
                            requirement_id=m.requirement_id,
                            status="MISSING",
                            evidence=None,
                            source_document=app_doc.filename,
                            source_page=None,
                            source_section=None,
                            confidence=0.0,
                            reasoning=f"Overridden to MISSING: Citation page {m.source_page} exceeds document bounds (total pages: {app_doc.page_count})."
                        )
                    )
                    continue

            # 2. Verify Quoted Evidence Text
            citation_page = m.source_page
            quote_clean = normalize(m.evidence) if m.evidence else ""
            if m.evidence:
                matching_pages = [
                    page_number
                    for page_number, page_text in normalized_pages.items()
                    if quote_clean and quote_clean in page_text
                ]
                if citation_page is not None and citation_page not in matching_pages:
                    # Fabricated or non-verbatim quote detected.
                    verified_mappings.append(
                        RequirementMappingItem(
                            requirement_id=m.requirement_id,
                            status="MISSING",
                            evidence=None,
                            source_document=app_doc.filename,
                            source_page=None,
                            source_section=None,
                            confidence=0.0,
                            reasoning=(
                                f"Overridden to MISSING: Quoted evidence could not be verified verbatim on cited page "
                                f"{citation_page} in the supplied application text."
                            ),
                        )
                    )
                    continue
                if citation_page is None and matching_pages:
                    citation_page = matching_pages[0]
                elif not matching_pages:
                    verified_mappings.append(
                        RequirementMappingItem(
                            requirement_id=m.requirement_id,
                            status="MISSING",
                            evidence=None,
                            source_document=app_doc.filename,
                            source_page=None,
                            source_section=None,
                            confidence=0.0,
                            reasoning="Overridden to MISSING: Quoted evidence could not be verified verbatim in the supplied application text.",
                        )
                    )
                    continue

            citation_section = m.source_section
            if citation_section:
                cited_page = next(
                    (page for page in app_doc.pages if page["page_number"] == citation_page),
                    None,
                )
                section_present = cited_page and normalize(citation_section) in normalize(cited_page["text"])
                if not section_present:
                    citation_section = None

            verified_mappings.append(
                m.model_copy(
                    update={
                        "source_document": app_doc.filename,
                        "evidence": m.evidence if m.status != "MISSING" else None,
                        "source_page": citation_page if m.status != "MISSING" else None,
                        "source_section": citation_section if m.status != "MISSING" else None,
                    }
                )
            )

        return verified_mappings
