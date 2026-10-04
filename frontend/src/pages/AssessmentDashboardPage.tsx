import React, { useState, useEffect } from 'react';
import { api } from '../api/client';
import { AssessmentDetail, RequirementDetail, ScoreBreakdown, ReviewerDecision, MappingStatus } from '../types';
import { StaleWarningBanner } from '../components/StaleWarningBanner';
import { StatusBadge, ReviewDecisionBadge, FinalAssessmentBadge, RequirementTypeBadge } from '../components/StatusBadge';
import { RequirementReviewModal } from '../components/RequirementReviewModal';
import {
  CheckCircle2,
  AlertTriangle,
  AlertCircle,
  HelpCircle,
  FileText,
  Search,
  RefreshCw,
  Eye,
  FileCheck2,
  ArrowRight,
  Bot,
  UserCheck,
  ShieldCheck,
  Quote,
} from 'lucide-react';

interface Props {
  assessmentId: string;
  onNavigate: (tab: 'dashboard' | 'supporting' | 'summary') => void;
}

export const AssessmentDashboardPage: React.FC<Props> = ({ assessmentId, onNavigate }) => {
  const [assessment, setAssessment] = useState<AssessmentDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [reanalyzing, setReanalyzing] = useState(false);
  const [selectedReq, setSelectedReq] = useState<RequirementDetail | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('ALL');
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [typeFilter, setTypeFilter] = useState<'ALL' | 'MANDATORY' | 'RECOMMENDATION'>('ALL');

  const loadData = async () => {
    try {
      setLoading(true);
      const detail = await api.getAssessment(assessmentId);
      setAssessment(detail);
    } catch (err) {
      console.error('Failed to load assessment data:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [assessmentId]);

  const handleReanalyze = async () => {
    if (!assessment) return;
    setReanalyzing(true);
    try {
      await api.analyzeAssessment(assessment.id);
      await loadData();
    } catch (err) {
      console.error('Failed to reanalyze:', err);
    } finally {
      setReanalyzing(false);
    }
  };

  const handleSubmitReview = async (
    requirementId: string,
    decision: ReviewerDecision,
    overrideStatus?: MappingStatus | null,
    notes?: string | null,
    overrideEvidence?: string | null
  ) => {
    await api.submitReview(assessmentId, requirementId, {
      decision,
      override_status: overrideStatus,
      reviewer_notes: notes,
      override_evidence: overrideEvidence,
    });
    setSelectedReq(null);
    await loadData();
  };

  if (loading && !assessment) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[50vh] text-slate-500">
        <RefreshCw className="w-8 h-8 animate-spin text-blue-600 mb-3" />
        <p className="text-sm font-medium">Loading assessment workbench...</p>
      </div>
    );
  }

  if (!assessment) {
    return (
      <div className="p-8 text-center text-slate-500">
        Assessment not found or failed to load.
      </div>
    );
  }

  const reqs = assessment.requirements || [];
  const score: ScoreBreakdown | null = assessment.score || null;

  // Filter requirements
  const filteredReqs = reqs.filter((r) => {
    const textMatch =
      r.text.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (r.source_section && r.source_section.toLowerCase().includes(searchQuery.toLowerCase())) ||
      (r.evidence && r.evidence.toLowerCase().includes(searchQuery.toLowerCase()));

    const catMatch = categoryFilter === 'ALL' || r.category === categoryFilter;
    const typeMatch =
      typeFilter === 'ALL' ||
      (typeFilter === 'MANDATORY' && r.mandatory) ||
      (typeFilter === 'RECOMMENDATION' && !r.mandatory);

    const effStatus = r.effective_status || 'MISSING';
    const statusMatch =
      statusFilter === 'ALL' ||
      (statusFilter === 'COMPLETE' && effStatus === 'SUPPORTED') ||
      (statusFilter === 'INCOMPLETE' && effStatus !== 'SUPPORTED') ||
      effStatus === statusFilter;

    return textMatch && catMatch && typeMatch && statusMatch;
  });

  const categories = Array.from(new Set(reqs.map((r) => r.category)));

  return (
    <div className="max-w-7xl mx-auto py-6 px-4 sm:px-6 space-y-6">
      {/* Stale Warning Banner */}
      {assessment.is_stale && (
        <StaleWarningBanner
          reason={assessment.stale_reason}
          onReanalyze={handleReanalyze}
          isAnalyzing={reanalyzing}
        />
      )}

      {/* Analysis Failed / Error Banner */}
      {(assessment.status === 'ANALYSIS_FAILED' || assessment.status === 'ERROR') && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="flex items-start gap-3">
            <AlertCircle className="w-5 h-5 text-red-600 mt-0.5 shrink-0" />
            <div>
              <h3 className="text-sm font-bold text-red-900">Analysis Failed</h3>
              <p className="text-xs text-red-700 mt-0.5">
                The AI document review pipeline encountered an error extracting requirements or readable text from the uploaded guidelines. Please verify that the documents contain readable text and retry analysis.
              </p>
            </div>
          </div>
          <button
            onClick={handleReanalyze}
            disabled={reanalyzing}
            className="inline-flex items-center justify-center gap-1.5 px-4 py-2 text-xs font-semibold text-white bg-red-600 hover:bg-red-700 rounded-lg shadow-xs transition-colors shrink-0 disabled:opacity-60 cursor-pointer"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${reanalyzing ? 'animate-spin' : ''}`} />
            {reanalyzing ? 'Retrying Analysis...' : 'Retry Analysis'}
          </button>
        </div>
      )}

      {/* Header Info Card */}
      <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-xs">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-100 pb-5">
          <div>
            <div className="flex items-center gap-2.5">
              <span className="text-xs font-semibold px-2 py-0.5 rounded bg-slate-100 text-slate-700 uppercase tracking-wider">
                Assessment
              </span>
              <span className="text-xs font-bold px-2.5 py-0.5 rounded-full bg-blue-50 text-blue-700 border border-blue-200">
                {assessment.status}
              </span>
              {assessment.is_stale && (
                <span className="text-xs font-bold px-2 py-0.5 rounded bg-amber-100 text-amber-900 border border-amber-300">
                  STALE
                </span>
              )}
            </div>
            <h1 className="text-xl font-bold text-slate-900 mt-1.5">{assessment.application_name}</h1>
            <p className="text-xs text-slate-500 mt-0.5">
              Guideline benchmark: <span className="font-medium text-slate-700">{assessment.grant_name}</span>
            </p>
          </div>

          {/* Quick Action Navigation */}
          <div className="flex items-center gap-2">
            <button
              onClick={() => onNavigate('supporting')}
              className="inline-flex items-center gap-1.5 px-3 py-2 text-xs font-semibold text-slate-700 bg-slate-100 hover:bg-slate-200 rounded-lg transition-colors"
            >
              <FileCheck2 className="w-3.5 h-3.5 text-slate-500" />
              Supporting Docs ({assessment.supporting_documents?.length || 0})
            </button>
            <button
              onClick={() => onNavigate('summary')}
              className="inline-flex items-center gap-1.5 px-4 py-2 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded-lg shadow-xs transition-colors"
            >
              View Reviewed Summary
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>

        {/* Metrics Row */}
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4 pt-5">
          <div className="bg-slate-50 p-3.5 rounded-lg border border-slate-100">
            <p className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">
              Deterministic Score
            </p>
            <div className="flex items-baseline gap-1 mt-1">
              <span className="text-2xl font-black text-slate-900">
                {score ? score.completion_percentage.toFixed(0) : '0'}%
              </span>
              <span className="text-[11px] text-slate-500 font-medium">mandatory</span>
            </div>
            <div className="w-full bg-slate-200 h-1.5 rounded-full overflow-hidden mt-2">
              <div
                className="bg-blue-600 h-1.5 rounded-full transition-all"
                style={{ width: `${score ? score.completion_percentage : 0}%` }}
              ></div>
            </div>
          </div>

          <div className="bg-slate-50 p-3.5 rounded-lg border border-slate-100">
            <p className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">
              Total Requirements
            </p>
            <p className="text-2xl font-black text-slate-900 mt-1">
              {score?.total_requirements ?? reqs.length}
            </p>
            <p className="text-[11px] text-slate-500 mt-0.5">
              {score?.total_mandatory ?? 0} mandatory
            </p>
          </div>

          <div className="bg-slate-50 p-3.5 rounded-lg border border-slate-100">
            <p className="text-[11px] font-semibold text-teal-700 uppercase tracking-wider">
              Human Confirmed
            </p>
            <p className="text-2xl font-black text-teal-800 mt-1">
              {score?.confirmed_count ?? 0}
            </p>
            <p className="text-[11px] text-teal-600 mt-0.5">accepted by reviewer</p>
          </div>

          <div className="bg-slate-50 p-3.5 rounded-lg border border-slate-100">
            <p className="text-[11px] font-semibold text-emerald-700 uppercase tracking-wider">
              Final Complete
            </p>
            <p className="text-2xl font-black text-emerald-800 mt-1">
              {score?.mandatory_completed ?? 0}
            </p>
            <p className="text-[11px] text-emerald-600 mt-0.5">satisfies criteria</p>
          </div>

          <div className="bg-slate-50 p-3.5 rounded-lg border border-slate-100">
            <p className="text-[11px] font-semibold text-rose-700 uppercase tracking-wider">
              Missing Evidence
            </p>
            <p className="text-2xl font-black text-rose-800 mt-1">
              {score?.mandatory_missing ?? 0}
            </p>
            <p className="text-[11px] text-rose-600 mt-0.5">critical gaps</p>
          </div>

          <div className="bg-slate-50 p-3.5 rounded-lg border border-slate-100">
            <p className="text-[11px] font-semibold text-amber-700 uppercase tracking-wider">
              Weak / Ambiguous
            </p>
            <p className="text-2xl font-black text-amber-800 mt-1">
              {(score?.mandatory_weak ?? 0) + (score?.mandatory_ambiguous ?? 0)}
            </p>
            <p className="text-[11px] text-amber-600 mt-0.5">needs revision</p>
          </div>
        </div>

        {/* Version Information Footnote */}
        <div className="mt-4 pt-3 border-t border-slate-100 flex flex-wrap items-center justify-between text-[11px] text-slate-500 gap-2">
          <div className="flex items-center gap-4">
            <span>
              Guideline Doc:{' '}
              <strong className="text-slate-700">
                v{assessment.active_guideline?.version_number ?? 1}
              </strong>
            </span>
            <span>
              Application Doc:{' '}
              <strong className="text-slate-700">
                v{assessment.active_application?.version_number ?? 1}
              </strong>
            </span>
            <span>
              Status: <strong className="text-slate-700">{assessment.status}</strong>
            </span>
          </div>
          {assessment.is_stale && (
            <button
              onClick={handleReanalyze}
              disabled={reanalyzing}
              className="text-amber-800 font-semibold hover:underline inline-flex items-center gap-1"
            >
              <RefreshCw className={`w-3 h-3 ${reanalyzing ? 'animate-spin' : ''}`} />
              Re-analyze now
            </button>
          )}
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-xs flex flex-col md:flex-row gap-3 items-center justify-between">
        <div className="relative w-full md:w-80">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
          <input
            type="text"
            placeholder="Search requirement, citation, or evidence..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-3 py-1.5 text-xs border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-600"
          />
        </div>

        <div className="flex flex-wrap items-center gap-2 w-full md:w-auto">
          {/* Classification Filter */}
          <select
            value={typeFilter}
            onChange={(e: any) => setTypeFilter(e.target.value)}
            className="text-xs border border-slate-300 rounded-lg px-2.5 py-1.5 bg-white text-slate-700 focus:outline-none"
          >
            <option value="ALL">All Types</option>
            <option value="MANDATORY">Mandatory Only</option>
            <option value="RECOMMENDATION">Recommendations</option>
          </select>

          {/* Status Filter */}
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="text-xs border border-slate-300 rounded-lg px-2.5 py-1.5 bg-white text-slate-700 focus:outline-none"
          >
            <option value="ALL">All Final Statuses</option>
            <option value="COMPLETE">Final Complete (Supported)</option>
            <option value="INCOMPLETE">Final Incomplete</option>
            <option value="WEAK">Weak Evidence</option>
            <option value="MISSING">Missing Evidence</option>
            <option value="AMBIGUOUS">Ambiguous Evidence</option>
          </select>

          {/* Category Filter */}
          {categories.length > 0 && (
            <select
              value={categoryFilter}
              onChange={(e) => setCategoryFilter(e.target.value)}
              className="text-xs border border-slate-300 rounded-lg px-2.5 py-1.5 bg-white text-slate-700 focus:outline-none"
            >
              <option value="ALL">All Categories</option>
              {categories.map((c) => (
                <option key={c} value={c}>
                  {c.toUpperCase()}
                </option>
              ))}
            </select>
          )}
        </div>
      </div>

      {/* Requirements Table / Card List */}
      <div className="bg-white border border-slate-200 rounded-xl shadow-xs overflow-hidden">
        <div className="px-5 py-3 border-b border-slate-200 bg-slate-50/70 flex items-center justify-between">
          <h2 className="text-xs font-bold uppercase tracking-wider text-slate-700">
            Guideline Requirements & Human-in-the-Loop Review ({filteredReqs.length} of {reqs.length})
          </h2>
          <span className="text-[11px] text-slate-500 font-medium">
            AI results preserved &bull; Reviewer overrides govern final deterministic completion
          </span>
        </div>

        {filteredReqs.length === 0 ? (
          <div className="p-12 text-center text-slate-500">
            <FileText className="w-8 h-8 text-slate-300 mx-auto mb-2" />
            <p className="text-sm font-semibold text-slate-700">No matching requirements</p>
            <p className="text-xs text-slate-400 mt-1">Adjust search or filters to see requirements.</p>
          </div>
        ) : (
          <div className="divide-y divide-slate-100">
            {filteredReqs.map((req) => {
              return (
                <div
                  key={req.id}
                  className="p-5 hover:bg-slate-50/70 transition-colors flex flex-col md:flex-row gap-4 justify-between items-start"
                >
                  <div className="space-y-3 flex-1">
                    {/* Header Badges */}
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="text-xs font-mono font-bold text-slate-500 bg-slate-100 px-2 py-0.5 rounded">
                        {req.req_id_code}
                      </span>
                      <RequirementTypeBadge mandatory={req.mandatory} typeStr={req.type} />
                      <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-slate-100 text-slate-700 uppercase tracking-wider border border-slate-200">
                        {req.category}
                      </span>
                    </div>

                    {/* Requirement Text */}
                    <p className="text-sm font-bold text-slate-900 leading-snug">{req.text}</p>

                    {/* Guideline Citation */}
                    <p className="text-xs text-slate-500">
                      Guideline Source:{' '}
                      <span className="font-medium text-slate-700">
                        {req.source_section || 'General'}
                        {req.source_page ? ` (p. ${req.source_page})` : ''}
                      </span>
                    </p>

                    {/* THREE-WAY DISTINCTION PANEL: AI vs Reviewer vs Final */}
                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5 pt-1">
                      {/* 1. AI Assessment */}
                      <div className="p-2.5 rounded-lg bg-blue-50/70 border border-blue-200 space-y-1">
                        <div className="flex items-center gap-1 text-[10px] font-bold text-blue-900 uppercase">
                          <Bot className="w-3 h-3 text-blue-600" />
                          AI Assessment
                        </div>
                        <div>
                          <StatusBadge status={req.ai_status || 'MISSING'} size="sm" />
                        </div>
                        {req.confidence != null && (
                          <p className="text-[10px] text-blue-800">
                            Confidence: {(req.confidence * 100).toFixed(0)}%
                          </p>
                        )}
                        <p className="text-[11px] text-blue-900/80 italic line-clamp-2">
                          {req.reasoning || 'No AI reasoning.'}
                        </p>
                      </div>

                      {/* 2. Reviewer Decision */}
                      <div className="p-2.5 rounded-lg bg-purple-50/70 border border-purple-200 space-y-1">
                        <div className="flex items-center gap-1 text-[10px] font-bold text-purple-900 uppercase">
                          <UserCheck className="w-3 h-3 text-purple-600" />
                          Reviewer Decision
                        </div>
                        <div>
                          <ReviewDecisionBadge decision={req.reviewer_decision} size="sm" />
                        </div>
                        {req.reviewed_at && (
                          <p className="text-[10px] text-purple-700">
                            {new Date(req.reviewed_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                          </p>
                        )}
                        {req.reviewer_notes ? (
                          <p className="text-[11px] text-purple-900/80 font-medium line-clamp-2">
                            "{req.reviewer_notes}"
                          </p>
                        ) : (
                          <p className="text-[11px] text-purple-500 italic">No human decision yet</p>
                        )}
                      </div>

                      {/* 3. Final Assessment */}
                      <div className="p-2.5 rounded-lg bg-emerald-50/70 border border-emerald-200 space-y-1">
                        <div className="flex items-center gap-1 text-[10px] font-bold text-emerald-900 uppercase">
                          <ShieldCheck className="w-3 h-3 text-emerald-700" />
                          Final Assessment
                        </div>
                        <div>
                          <FinalAssessmentBadge
                            isComplete={req.is_final_complete}
                            effectiveStatus={req.effective_status}
                            size="sm"
                          />
                        </div>
                        <p className="text-[11px] text-emerald-900/80 font-medium pt-0.5">
                          {req.is_final_complete ? 'Complete (100%)' : 'Incomplete (0%)'}
                        </p>
                      </div>
                    </div>

                    {/* Quoted Application Evidence Citation */}
                    <div className="text-xs rounded-lg p-2.5 bg-slate-50 border border-slate-200/80 space-y-1">
                      <div className="flex items-center justify-between text-[11px] text-slate-500 font-medium">
                        <span className="flex items-center gap-1 text-slate-700 font-semibold">
                          <Quote className="w-3 h-3 text-slate-400" />
                          Application Evidence Quoted:
                        </span>
                        <span>
                          {req.evidence_page ? `Page ${req.evidence_page}` : 'No page'}
                          {req.evidence_section ? ` • ${req.evidence_section}` : ''}
                        </span>
                      </div>
                      <p className="italic text-slate-800 text-xs">
                        {req.reviewer_evidence || req.evidence
                          ? `"${req.reviewer_evidence || req.evidence}"`
                          : 'No supporting text found in draft application.'}
                      </p>
                    </div>
                  </div>

                  {/* Review Action Trigger Button */}
                  <div className="shrink-0 pt-1">
                    <button
                      onClick={() => setSelectedReq(req)}
                      className="inline-flex items-center gap-1.5 px-3 py-2 text-xs font-bold rounded-lg border border-slate-300 text-slate-800 bg-white hover:bg-blue-50 hover:border-blue-400 hover:text-blue-700 shadow-xs transition-all"
                    >
                      <Eye className="w-3.5 h-3.5" />
                      Review & Decision
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Review Modal */}
      {selectedReq && (
        <RequirementReviewModal
          requirement={selectedReq}
          onClose={() => setSelectedReq(null)}
          onSubmitReview={handleSubmitReview}
        />
      )}
    </div>
  );
};
