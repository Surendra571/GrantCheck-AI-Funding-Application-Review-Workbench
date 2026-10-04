from typing import List
from app.models.requirement import Requirement
from app.models.supporting_doc import SupportingDocument
from app.schemas.score import DeterministicScoreBreakdown

class ScoringService:
    """
    Deterministic scoring engine.
    Calculates completeness from verified requirements and human reviewer decisions.
    Never lets the LLM calculate or alter the final completion score.
    """

    @classmethod
    def calculate_score(
        cls,
        requirements: List[Requirement],
        supporting_docs: List[SupportingDocument] = None
    ) -> DeterministicScoreBreakdown:
        total_reqs = len(requirements)
        mandatory_reqs = [r for r in requirements if r.mandatory]
        recommendation_reqs = [r for r in requirements if not r.mandatory]

        total_mandatory = len(mandatory_reqs)
        total_recommendations = len(recommendation_reqs)

        mandatory_completed = 0
        mandatory_weak = 0
        mandatory_missing = 0
        mandatory_ambiguous = 0
        recommendations_addressed = 0

        confirmed_count = 0
        corrected_count = 0
        rejected_count = 0
        pending_count = 0

        for r in requirements:
            m = r.mapping
            eff_status = m.effective_status if m else "MISSING"
            rev_dec = m.reviewer_decision if m else "PENDING"

            if rev_dec == "CONFIRMED":
                confirmed_count += 1
            elif rev_dec == "CORRECTED":
                corrected_count += 1
            elif rev_dec == "REJECTED":
                rejected_count += 1
            else:
                pending_count += 1

            if r.mandatory:
                if eff_status == "SUPPORTED":
                    mandatory_completed += 1
                elif eff_status == "WEAK":
                    mandatory_weak += 1
                elif eff_status == "AMBIGUOUS":
                    mandatory_ambiguous += 1
                else:  # MISSING or unknown
                    mandatory_missing += 1
            elif eff_status == "SUPPORTED":
                recommendations_addressed += 1

        if total_mandatory > 0:
            completion_pct = round((mandatory_completed / total_mandatory) * 100.0, 1)
        else:
            completion_pct = 0.0

        # Supporting docs breakdown
        docs = supporting_docs or []
        req_docs = [d for d in docs if d.is_required]
        supplied_req_docs = sum(1 for d in req_docs if d.is_supplied)
        missing_req_docs = len(req_docs) - supplied_req_docs

        return DeterministicScoreBreakdown(
            total_requirements=total_reqs,
            total_mandatory=total_mandatory,
            total_recommendations=total_recommendations,
            recommendations_total=total_recommendations,
            recommendations_addressed=recommendations_addressed,
            completed=mandatory_completed,
            incomplete=total_mandatory - mandatory_completed,
            mandatory_completed=mandatory_completed,
            mandatory_weak=mandatory_weak,
            mandatory_missing=mandatory_missing,
            mandatory_ambiguous=mandatory_ambiguous,
            confirmed_count=confirmed_count,
            corrected_count=corrected_count,
            rejected_count=rejected_count,
            pending_count=pending_count,
            completion_percentage=completion_pct,
            total_required_docs=len(req_docs),
            supplied_required_docs=supplied_req_docs,
            missing_required_docs=missing_req_docs,
        )
