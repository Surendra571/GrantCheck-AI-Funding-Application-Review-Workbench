export type MappingStatus = 'SUPPORTED' | 'WEAK' | 'MISSING' | 'AMBIGUOUS';

export type ReviewerDecision = 'PENDING' | 'CONFIRMED' | 'CORRECTED' | 'REJECTED';

export type RequirementType = 'mandatory' | 'recommendation' | 'eligibility-related' | 'submission-related';

export type RequirementCategory =
  | 'eligibility'
  | 'submission'
  | 'documentation'
  | 'project'
  | 'financial'
  | 'organisation'
  | 'recommendation'
  | 'other';

export interface DocumentVersion {
  id: string;
  doc_type: 'guideline' | 'application' | 'supporting';
  filename: string;
  file_hash: string;
  version_number: number;
  is_active: boolean;
  page_count: number;
  upload_timestamp: string;
}

export interface SupportingDocument {
  id: string;
  name: string;
  is_required: boolean;
  is_supplied: boolean;
  filename?: string | null;
  reviewer_notes?: string | null;
}

export interface ScoreBreakdown {
  total_requirements: number;
  total_mandatory: number;
  total_recommendations: number;
  recommendations_total: number;
  recommendations_addressed: number;
  completed: number;
  incomplete: number;
  mandatory_completed: number;
  mandatory_weak: number;
  mandatory_missing: number;
  mandatory_ambiguous: number;
  confirmed_count: number;
  corrected_count: number;
  rejected_count: number;
  pending_count: number;
  completion_percentage: number;
  total_required_docs: number;
  supplied_required_docs: number;
  missing_required_docs: number;
}

export interface RequirementDetail {
  id: string;
  req_id_code: string;
  text: string;
  type: RequirementType;
  mandatory: boolean;
  category: RequirementCategory;
  source_document: string;
  source_page?: number | null;
  source_section?: string | null;
  source_excerpt: string;

  // AI assessment fields (preserved)
  mapping_id?: string | null;
  ai_status?: MappingStatus | null;
  evidence?: string | null;
  evidence_source_doc?: string | null;
  evidence_page?: number | null;
  evidence_section?: string | null;
  confidence?: number | null;
  reasoning?: string | null;

  // Reviewer fields
  reviewer_decision: ReviewerDecision;
  reviewer_override_status?: MappingStatus | null;
  reviewer_notes?: string | null;
  reviewer_evidence?: string | null;
  reviewer_citation?: string | null;
  reviewed_at?: string | null;

  // Final effective assessment
  effective_status: MappingStatus;
  is_final_complete: boolean;
}

export interface AssessmentDetail {
  id: string;
  title: string;
  grant_name: string;
  application_name: string;
  status: 'DRAFT' | 'ANALYZING' | 'ANALYZED' | 'ANALYSIS_FAILED' | 'ERROR';
  is_stale: boolean;
  stale_reason?: string | null;
  raw_analysis_payload?: any;
  created_at: string;
  updated_at: string;

  active_guideline?: DocumentVersion | null;
  active_application?: DocumentVersion | null;
  document_versions: DocumentVersion[];

  score?: ScoreBreakdown | null;
  requirements: RequirementDetail[];
  supporting_documents: SupportingDocument[];
}

export interface AssessmentListItem {
  id: string;
  title: string;
  grant_name: string;
  application_name: string;
  status: string;
  is_stale: boolean;
  stale_reason?: string | null;
  created_at: string;
  updated_at: string;
  guideline_version?: number | null;
  application_version?: number | null;
  completion_percentage?: number | null;
}

export interface UnsupportedClaim {
  claim: string;
  source_page?: number | null;
  reason: string;
  related_requirement?: string | null;
  status: string;
}

export interface ClarificationQuestion {
  requirement_id?: string | null;
  question: string;
  gap_type: string;
  suggested_evidence: string;
}

export interface ReviewedSummaryReport {
  assessment_id: string;
  grant_name: string;
  application_name: string;
  guideline_version: number;
  application_version: number;
  guideline_hash: string;
  application_hash: string;
  is_stale: boolean;
  stale_reason?: string | null;
  score: ScoreBreakdown;
  unsupported_claims: UnsupportedClaim[];
  missing_documents: SupportingDocument[];
  clarification_questions: ClarificationQuestion[];
  reviewer_decisions_summary: Record<string, number>;
  raw_ai_audit_snapshot?: Record<string, any> | null;
  disclaimer: string;
}
