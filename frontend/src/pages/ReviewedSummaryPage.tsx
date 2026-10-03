import React, { useState, useEffect } from 'react';
import { api } from '../api/client';
import { ReviewedSummaryReport, UnsupportedClaim, ClarificationQuestion, SupportingDocument } from '../types';
import { DisclaimerBanner } from '../components/DisclaimerBanner';
import { StaleWarningBanner } from '../components/StaleWarningBanner';
import {
  FileCheck2,
  AlertTriangle,
  HelpCircle,
  FileQuestion,
  Printer,
  ArrowLeft,
  ChevronDown,
  ChevronUp,
  RefreshCw,
  Code,
  CheckCircle2,
  XCircle,
} from 'lucide-react';

interface Props {
  assessmentId: string;
  onNavigate: (tab: 'dashboard' | 'supporting' | 'summary') => void;
}

export const ReviewedSummaryPage: React.FC<Props> = ({ assessmentId, onNavigate }) => {
  const [summary, setSummary] = useState<ReviewedSummaryReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [showRawJson, setShowRawJson] = useState(false);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        const report = await api.getSummaryReport(assessmentId);
        setSummary(report);
      } catch (err) {
        console.error('Failed to load summary report:', err);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, [assessmentId]);

  if (loading && !summary) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[50vh] text-slate-500">
        <RefreshCw className="w-8 h-8 animate-spin text-blue-600 mb-3" />
        <p className="text-sm font-medium">Generating reviewed summary...</p>
      </div>
    );
  }

  if (!summary) {
    return (
      <div className="p-8 text-center text-slate-500">
        Reviewed summary could not be retrieved.
      </div>
    );
  }

  const handlePrint = () => {
    window.print();
  };

  const score = summary.score;
  const isStale = summary.is_stale;

  return (
    <div className="max-w-5xl mx-auto py-6 px-4 sm:px-6 space-y-6 print:p-0">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 print:hidden">
        <div>
          <button
            onClick={() => onNavigate('dashboard')}
            className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-500 hover:text-slate-800 mb-2 transition-colors"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            Back to Assessment Dashboard
          </button>
          <h1 className="text-xl font-bold text-slate-900">Reviewed Completeness & Evidence Summary</h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Formal assessment report detailing deterministic score, verified evidence, unsupported claims, and reviewer decisions.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={handlePrint}
            className="inline-flex items-center gap-1.5 px-3 py-2 text-xs font-semibold text-slate-700 bg-white border border-slate-300 hover:bg-slate-50 rounded-lg shadow-xs transition-colors"
          >
            <Printer className="w-3.5 h-3.5" />
            Export / Print Summary
          </button>
        </div>
      </div>

      <DisclaimerBanner />

      {isStale && (
        <StaleWarningBanner
          reason={summary.stale_reason || 'A source document has changed since this summary was generated.'}
          onReanalyze={() => onNavigate('dashboard')}
        />
      )}

      <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-xs space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-100 pb-4">
          <div>
            <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-blue-50 text-blue-700 uppercase tracking-wider">
              Grant Application Review Report
            </span>
            <h2 className="text-lg font-bold text-slate-900 mt-1">{summary.application_name}</h2>
            <p className="text-xs text-slate-500">
              Guideline Evaluated: <span className="font-semibold text-slate-700">{summary.grant_name}</span>
            </p>
          </div>
          <div className="text-right text-xs text-slate-500">
            <p className="mt-0.5 font-mono text-[11px]">
              ID: {summary.assessment_id.slice(0, 13)}...
            </p>
          </div>
        </div>

        <div className="bg-gradient-to-br from-slate-900 to-slate-800 text-white rounded-xl p-6 flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div className="space-y-1 max-w-lg">
            <span className="text-xs font-bold text-blue-400 uppercase tracking-widest">
              Deterministic Checklist Completion
            </span>
            <div className="flex items-baseline gap-2">
              <span className="text-4xl font-black tracking-tight">
                {score.completion_percentage.toFixed(1)}%
              </span>
              <span className="text-xs text-slate-300 font-medium">
                ({score.mandatory_completed} of {score.total_mandatory} mandatory criteria satisfied)
              </span>
            </div>
            <p className="text-xs text-slate-400 pt-1 leading-relaxed">
              Calculated deterministically by backend rules: complete mandatory requirements divided by total mandatory requirements. Recommendation items are isolated and do not reduce the mandatory completion percentage.
            </p>
          </div>

          <div className="grid grid-cols-2 gap-3 text-xs shrink-0">
            <div className="bg-white/10 p-2.5 rounded-lg border border-white/10">
              <p className="text-slate-300 text-[10px] uppercase font-semibold">Human Confirmed</p>
              <p className="text-lg font-bold text-teal-400 mt-0.5">
                {score.confirmed_count}
              </p>
            </div>
            <div className="bg-white/10 p-2.5 rounded-lg border border-white/10">
              <p className="text-slate-300 text-[10px] uppercase font-semibold">Missing Evidence</p>
              <p className="text-lg font-bold text-rose-400 mt-0.5">
                {score.mandatory_missing}
              </p>
            </div>
            <div className="bg-white/10 p-2.5 rounded-lg border border-white/10">
              <p className="text-slate-300 text-[10px] uppercase font-semibold">Weak Evidence</p>
              <p className="text-lg font-bold text-amber-400 mt-0.5">{score.mandatory_weak}</p>
            </div>
            <div className="bg-white/10 p-2.5 rounded-lg border border-white/10">
              <p className="text-slate-300 text-[10px] uppercase font-semibold">Ambiguous Evidence</p>
              <p className="text-lg font-bold text-purple-400 mt-0.5">
                {score.mandatory_ambiguous}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Unsupported Claims Section (Rule: State only that no evidence exists, do NOT call false) */}
      <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-xs space-y-4">
        <div className="flex items-center gap-2 border-b border-slate-100 pb-3">
          <AlertTriangle className="w-5 h-5 text-amber-500" />
          <div>
            <h3 className="text-sm font-bold text-slate-900">
              Unsupported Application Claims ({summary.unsupported_claims.length})
            </h3>
            <p className="text-xs text-slate-500">
              Substantive claims in the draft application where no supporting evidence or third-party documentation was supplied.
            </p>
          </div>
        </div>

        {summary.unsupported_claims.length === 0 ? (
          <p className="text-xs text-slate-500 italic p-2">
            No unverified claims detected in application materials.
          </p>
        ) : (
          <div className="space-y-3">
            {summary.unsupported_claims.map((claim: UnsupportedClaim, idx: number) => (
              <div
                key={idx}
                className="p-4 rounded-lg bg-amber-50/50 border border-amber-200/70 space-y-1.5 text-xs"
              >
                <div className="flex items-center justify-between text-[11px]">
                  <span className="font-bold text-amber-900">
                    Application Claim {idx + 1}
                    {claim.source_page ? ` (p. ${claim.source_page})` : ''}
                  </span>
                  <span className="font-medium text-amber-800 bg-amber-100 px-2 py-0.5 rounded border border-amber-200">
                    No supporting evidence found in supplied materials
                  </span>
                </div>
                <p className="font-semibold text-slate-900 italic">"{claim.claim}"</p>
                <p className="text-slate-600">
                  <span className="font-medium text-slate-800">Reason:</span> {claim.reason}
                </p>
                {claim.related_requirement && (
                  <p className="text-[11px] text-slate-500">
                    Related Requirement: <span className="font-mono">{claim.related_requirement}</span>
                  </p>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Clarification Questions */}
      <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-xs space-y-4">
        <div className="flex items-center gap-2 border-b border-slate-100 pb-3">
          <FileQuestion className="w-5 h-5 text-blue-600" />
          <div>
            <h3 className="text-sm font-bold text-slate-900">
              Actionable Clarification Questions ({summary.clarification_questions.length})
            </h3>
            <p className="text-xs text-slate-500">
              AI-generated inquiries for the applicant to address identified gaps, missing data, and ambiguities.
            </p>
          </div>
        </div>

        {summary.clarification_questions.length === 0 ? (
          <p className="text-xs text-slate-500 italic p-2">
            No clarification questions required — application satisfies criteria.
          </p>
        ) : (
          <div className="divide-y divide-slate-100">
            {summary.clarification_questions.map((q: ClarificationQuestion, idx: number) => (
              <div key={idx} className="py-3 text-xs space-y-1">
                <div className="flex items-center gap-2">
                  <span className="font-bold text-slate-800">Q{idx + 1}:</span>
                  <span className="font-semibold text-slate-900">{q.question}</span>
                  <span className="ml-auto text-[10px] font-bold px-1.5 py-0.5 rounded uppercase bg-amber-100 text-amber-800">
                    {q.gap_type}
                  </span>
                </div>
                <div className="text-[11px] text-slate-500 flex items-center gap-3">
                  <span>Requirement: <code className="font-mono text-slate-700">{q.requirement_id || 'General'}</code></span>
                  <span>Suggested evidence: {q.suggested_evidence}</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Supporting Documents Status */}
      <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-xs space-y-4">
        <div className="flex items-center gap-2 border-b border-slate-100 pb-3">
          <FileCheck2 className="w-5 h-5 text-slate-700" />
          <h3 className="text-sm font-bold text-slate-900">
            Missing Mandatory Supporting Documents ({summary.missing_documents.length})
          </h3>
        </div>

        {summary.missing_documents.length === 0 ? (
          <p className="text-xs text-emerald-700 p-2 font-medium flex items-center gap-1.5">
            <CheckCircle2 className="w-4 h-4 text-emerald-600" />
            All required supporting attachments have been verified as supplied.
          </p>
        ) : (
          <div className="space-y-2 text-xs">
            {summary.missing_documents.map((doc: SupportingDocument, idx: number) => (
              <div
                key={idx}
                className="flex items-center justify-between p-3 rounded-lg bg-rose-50 border border-rose-200"
              >
                <div className="flex items-center gap-2">
                  <XCircle className="w-4 h-4 text-rose-600 shrink-0" />
                  <span className="font-semibold text-rose-900">{doc.name}</span>
                  {doc.is_required && (
                    <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-rose-100 text-rose-800">
                      MANDATORY
                    </span>
                  )}
                </div>
                <span className="text-[11px] font-bold px-2 py-0.5 rounded bg-rose-200 text-rose-900">
                  NOT SUPPLIED
                </span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Reviewer Decisions Log */}
      <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-xs space-y-4">
        <h3 className="text-sm font-bold text-slate-900 border-b border-slate-100 pb-3">
          Human Reviewer Override Decisions Summary
        </h3>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
          <div className="p-3 bg-teal-50 rounded-lg border border-teal-200">
            <span className="text-teal-700 uppercase font-semibold text-[10px]">Confirmed</span>
            <p className="text-lg font-bold text-teal-800 mt-0.5">
              {summary.reviewer_decisions_summary['CONFIRMED'] || 0}
            </p>
          </div>
          <div className="p-3 bg-blue-50 rounded-lg border border-blue-200">
            <span className="text-blue-700 uppercase font-semibold text-[10px]">Corrected</span>
            <p className="text-lg font-bold text-blue-800 mt-0.5">
              {summary.reviewer_decisions_summary['CORRECTED'] || 0}
            </p>
          </div>
          <div className="p-3 bg-rose-50 rounded-lg border border-rose-200">
            <span className="text-rose-700 uppercase font-semibold text-[10px]">Rejected</span>
            <p className="text-lg font-bold text-rose-800 mt-0.5">
              {summary.reviewer_decisions_summary['REJECTED'] || 0}
            </p>
          </div>
          <div className="p-3 bg-slate-50 rounded-lg border border-slate-200">
            <span className="text-slate-500 uppercase font-semibold text-[10px]">Pending Review</span>
            <p className="text-lg font-bold text-slate-600 mt-0.5">
              {summary.reviewer_decisions_summary['PENDING'] || 0}
            </p>
          </div>
        </div>
      </div>

      {/* Version Information & Content Hashes */}
      <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-xs space-y-3 text-xs text-slate-600">
        <h3 className="text-sm font-bold text-slate-900 border-b border-slate-100 pb-2">
          Document Version Audit Trail
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="p-3 bg-slate-50 rounded-lg border border-slate-200 font-mono text-[11px] space-y-1">
            <p className="font-sans font-bold text-slate-800 text-xs">Guideline Version</p>
            <p>Version Number: v{summary.guideline_version}</p>
            <p className="truncate">SHA-256: {summary.guideline_hash}</p>
          </div>
          <div className="p-3 bg-slate-50 rounded-lg border border-slate-200 font-mono text-[11px] space-y-1">
            <p className="font-sans font-bold text-slate-800 text-xs">Application Version</p>
            <p>Version Number: v{summary.application_version}</p>
            <p className="truncate">SHA-256: {summary.application_hash}</p>
          </div>
        </div>
      </div>

      {/* Collapsible Raw AI Audit Snapshot */}
      {summary.raw_ai_audit_snapshot && (
        <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-xs space-y-3 print:hidden">
          <button
            onClick={() => setShowRawJson(!showRawJson)}
            className="w-full flex items-center justify-between text-left"
          >
            <div className="flex items-center gap-2">
              <Code className="w-4 h-4 text-slate-600" />
              <h3 className="text-sm font-bold text-slate-900">
                Inspect Raw AI Pipeline Audit Snapshot
              </h3>
            </div>
            {showRawJson ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
          </button>
          <p className="text-xs text-slate-500">
            Audit trail of exact structured JSON outputs produced by the controlled 8-step pipeline stored in database.
          </p>

          {showRawJson && (
            <pre className="mt-3 p-4 bg-slate-900 text-slate-100 rounded-lg text-xs font-mono overflow-x-auto max-h-96">
              {JSON.stringify(summary.raw_ai_audit_snapshot, null, 2)}
            </pre>
          )}
        </div>
      )}
    </div>
  );
};
