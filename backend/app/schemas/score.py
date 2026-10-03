from pydantic import BaseModel, Field

class DeterministicScoreBreakdown(BaseModel):
    total_requirements: int = 0
    total_mandatory: int = 0
    total_recommendations: int = 0
    mandatory_completed: int = 0
    mandatory_weak: int = 0
    mandatory_missing: int = 0
    mandatory_ambiguous: int = 0
    confirmed_count: int = 0
    corrected_count: int = 0
    rejected_count: int = 0
    pending_count: int = 0
    completion_percentage: float = 0.0
    total_required_docs: int = 0
    supplied_required_docs: int = 0
    missing_required_docs: int = 0
