import {
  AssessmentDetail,
  AssessmentListItem,
  DocumentVersion,
  ReviewedSummaryReport,
  SupportingDocument,
  ReviewerDecision,
  MappingStatus,
} from '../types';

const BASE_URL = '/api';

export class ApiError extends Error {
  status: number;
  errorType?: string;
  constructor(message: string, status: number, errorType?: string) {
    super(message);
    this.status = status;
    this.errorType = errorType;
  }
}

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(url, options);
  if (!res.ok) {
    let detail = `Error ${res.status}: ${res.statusText}`;
    let errorType: string | undefined;
    try {
      const data = await res.json();
      if (data.detail) detail = data.detail;
      if (data.error_type) errorType = data.error_type;
    } catch {
      // response wasn't json
    }
    throw new ApiError(detail, res.status, errorType);
  }
  if (res.status === 204) {
    return {} as T;
  }
  return res.json();
}

export const api = {
  getAssessments: () => request<AssessmentListItem[]>(`${BASE_URL}/assessments`),

  getAssessment: (id: string) => request<AssessmentDetail>(`${BASE_URL}/assessments/${id}`),

  createAssessment: (data: { title: string; grant_name: string; application_name: string }) =>
    request<AssessmentDetail>(`${BASE_URL}/assessments`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    }),

  deleteAssessment: (id: string) =>
    request<void>(`${BASE_URL}/assessments/${id}`, {
      method: 'DELETE',
    }),

  uploadDocument: (id: string, docType: 'guideline' | 'application' | 'supporting', file: File) => {
    const formData = new FormData();
    formData.append('doc_type', docType);
    formData.append('file', file);
    return request<DocumentVersion>(`${BASE_URL}/assessments/${id}/documents/upload`, {
      method: 'POST',
      body: formData,
    });
  },

  analyzeAssessment: (id: string) =>
    request<AssessmentDetail>(`${BASE_URL}/assessments/${id}/analyze`, {
      method: 'POST',
    }),

  submitReview: (
    assessmentId: string,
    requirementId: string,
    data: {
      decision: ReviewerDecision;
      override_status?: MappingStatus | null;
      reviewer_notes?: string | null;
      override_evidence?: string | null;
      override_citation?: string | null;
    }
  ) =>
    request<{
      mapping_id: string;
      requirement_id: string;
      ai_status: string;
      reviewer_decision: string;
      reviewer_override_status?: string;
      effective_status: string;
      reviewer_notes?: string;
      reviewed_at: string;
      message: string;
    }>(`${BASE_URL}/assessments/${assessmentId}/requirements/${requirementId}/review`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    }),

  getSupportingDocs: (assessmentId: string) =>
    request<SupportingDocument[]>(`${BASE_URL}/assessments/${assessmentId}/supporting-docs`),

  addSupportingDoc: (
    assessmentId: string,
    data: { name: string; is_required: boolean; is_supplied: boolean; filename?: string; reviewer_notes?: string }
  ) =>
    request<SupportingDocument>(`${BASE_URL}/assessments/${assessmentId}/supporting-docs`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    }),

  updateSupportingDoc: (
    assessmentId: string,
    docId: string,
    data: { is_supplied?: boolean; filename?: string; reviewer_notes?: string }
  ) =>
    request<SupportingDocument>(`${BASE_URL}/assessments/${assessmentId}/supporting-docs/${docId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    }),

  deleteSupportingDoc: (assessmentId: string, docId: string) =>
    request<void>(`${BASE_URL}/assessments/${assessmentId}/supporting-docs/${docId}`, {
      method: 'DELETE',
    }),

  getSummaryReport: (assessmentId: string) =>
    request<ReviewedSummaryReport>(`${BASE_URL}/assessments/${assessmentId}/summary`),
};
