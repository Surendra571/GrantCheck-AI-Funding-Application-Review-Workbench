import re
from typing import List
from app.services.parser import ParsedDocument
from app.schemas.ai import RequirementMappingItem

class CitationVerifier:
    """Anti-hallucination layer ensuring citations and quoted evidence strictly exist in supplied documents."""

    @staticmethod
    def verify_mappings(mappings: List[RequirementMappingItem], app_doc: ParsedDocument) -> List[RequirementMappingItem]:
        verified_mappings: List[RequirementMappingItem] = []
        app_text_clean = re.sub(r'\s+', ' ', app_doc.full_text).lower()

        for m in mappings:
            # 1. Verify Page Out-of-Bounds
            if m.source_page is not None:
                if m.source_page < 1 or m.source_page > app_doc.page_count:
                    # Fabricated page number detected
                    verified_mappings.append(
                        RequirementMappingItem(
                            requirement_id=m.requirement_id,
                            status="MISSING",
                            evidence=None,
                            source_document=m.source_document,
                            source_page=None,
                            source_section=None,
                            confidence=0.0,
                            reasoning=f"Overridden to MISSING: Citation page {m.source_page} exceeds document bounds (total pages: {app_doc.page_count})."
                        )
                    )
                    continue

            # 2. Verify Quoted Evidence Text
            if m.evidence:
                quote_clean = re.sub(r'\s+', ' ', m.evidence).strip().lower()
                # Check if significant portion of quote exists in document
                quote_words = [w for w in re.findall(r'\b\w+\b', quote_clean) if len(w) > 3]
                if quote_words:
                    matched_words = sum(1 for w in quote_words if w in app_text_clean)
                    overlap_ratio = matched_words / len(quote_words)
                    if overlap_ratio < 0.35:
                        # Fabricated quote detected
                        verified_mappings.append(
                            RequirementMappingItem(
                                requirement_id=m.requirement_id,
                                status="MISSING",
                                evidence=None,
                                source_document=m.source_document,
                                source_page=None,
                                source_section=None,
                                confidence=0.0,
                                reasoning="Overridden to MISSING: Quoted evidence could not be verified in the supplied application text."
                            )
                        )
                        continue

            verified_mappings.append(m)

        return verified_mappings
