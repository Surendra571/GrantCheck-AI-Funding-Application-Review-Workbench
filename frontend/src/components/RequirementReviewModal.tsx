import React, { useState } from 'react';
import {
  X,
  CheckCircle2,
  AlertTriangle,
  HelpCircle,
  XOctagon,
  CheckCheck,
  Edit3,
  Ban,
  Clock,
  Bot,
  UserCheck,
  ShieldCheck,
  ShieldAlert,
  Loader2,
  FileText,
  Quote,
} from 'lucide-react';
import { RequirementDetail, ReviewerDecision, MappingStatus } from '../types';
import { StatusBadge, ReviewDecisionBadge, FinalAssessmentBadge, RequirementTypeBadge } from './StatusBadge';

interface Props {
  requirement: RequirementDetail | null;
  onClose: () => void;
  onSubmitReview: (
    requirementId: string,
    decision: ReviewerDecision,
    overrideStatus?: MappingStatus | null,
    notes?: string | null,
    overrideEvidence?: string | null
  ) => Promise<void>;
}

export const RequirementReviewModal: React.FC<Props> = ({ requirement, onClose, onSubmitReview }) => {
  if (!requirement) return null;

  const [activeTab, setActiveTab] = useState<'confirm' | 'correct' | 'reject'>('confirm');
  const [overrideStatus, setOverrideStatus] = useState<MappingStatus>(
    (requirement.reviewer_override_status as MappingStatus) || 'SUPPORTED'
  );
  const [notes, setNotes] = useState<string>(requirement.reviewer_notes || '');
  const [overrideEvidence, setOverrideEvidence] = useState<string>(requirement.reviewer_evidence || requirement.evidence || '');
  const [submitting, setSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const handleAction = async (decision: ReviewerDecision) => {
    setErrorMsg(null);

    if (decision === 'CORRECTED') {
      if (!notes.trim()) {
        setErrorMsg('Reviewer notes are mandatory when correcting status.');
        return;
      }
    } else if (decision === 'REJECTED') {
      if (!notes.trim()) {
        setErrorMsg('Reviewer notes are mandatory when rejecting a requirement mapping.');
        return;
      }
    }

    setSubmitting(true);
    try {
      await onSubmitReview(
        requirement.id,
        decision,
        decision === 'CORRECTED' ? overrideStatus : null,
        notes.trim() || undefined,
        decision === 'CORRECTED' ? overrideEvidence.trim() || undefined : undefined
      );
      onClose();
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to submit review.');
    } finally {
      setSubmitting(false);
    }
  };

  // Preview what the final assessment will be based on current reviewer action
  const previewEffectiveStatus =
    activeTab === 'confirm'
      ? 'SUPPORTED'
      : activeTab === 'reject'
      ? 'MISSING'
      : overrideStatus;

  const previewIsComplete = previewEffectiveStatus === 'SUPPORTED';

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-2xl max-w-3xl w-full max-h-[92vh] flex flex-col border border-slate-200 overflow-hidden">
        {/* Modal Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100 bg-slate-50/80">
          <div className="flex items-center gap-2.5">
            <span className="font-mono text-xs font-bold text-slate-500 bg-slate-200 px-2 py-0.5 rounded">
              {requirement.req_id_code}
            </span>
            <RequirementTypeBadge mandatory={requirement.mandatory} typeStr={requirement.type} />
            <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-slate-100 text-slate-700 uppercase tracking-wider border border-slate-200">
              {requirement.category}
            </span>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-200 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-6 overflow-y-auto space-y-6">
          {/* Requirement Description */}
          <div className="space-y-1">
            <h2 className="text-base font-bold text-slate-900 leading-snug">{requirement.text}</h2>
            <p className="text-xs text-slate-500">
              Guideline Source:{' '}
              <span className="font-medium text-slate-700">
                {requirement.source_section || 'General'}
                {requirement.source_page ? ` (p. ${requirement.source_page})` : ''}
              </span>
            </p>
          </div>

          {/* THREE-WAY AUDIT COMPARISON: AI vs Reviewer vs Final */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            {/* Box 1: AI Output */}
            <div className="p-3.5 bg-blue-50/70 border border-blue-200 rounded-xl space-y-2">
              <div className="flex items-center gap-1.5 text-blue-900 font-bold text-xs uppercase tracking-wider">
                <Bot className="w-4 h-4 text-blue-600" />
                1. AI Assessment
              </div>
              <div className="pt-1">
                <StatusBadge status={requirement.ai_status || 'MISSING'} size="sm" />
              </div>
              {requirement.confidence != null && (
                <p className="text-[11px] text-blue-800 font-medium">
                  Confidence: {(requirement.confidence * 100).toFixed(0)}%
                </p>
              )}
              <p className="text-[11px] text-blue-900/80 leading-relaxed italic">
                {requirement.reasoning || 'No AI reasoning recorded.'}
              </p>
            </div>

            {/* Box 2: Reviewer Decision */}
            <div className="p-3.5 bg-purple-50/70 border border-purple-200 rounded-xl space-y-2">
              <div className="flex items-center gap-1.5 text-purple-900 font-bold text-xs uppercase tracking-wider">
                <UserCheck className="w-4 h-4 text-purple-600" />
                2. Reviewer Decision
              </div>
              <div className="pt-1">
                <ReviewDecisionBadge decision={requirement.reviewer_decision} size="sm" />
              </div>
              {requirement.reviewed_at && (
                <p className="text-[10px] text-purple-700 font-medium">
                  Reviewed: {new Date(requirement.reviewed_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                </p>
              )}
              {requirement.reviewer_notes ? (
                <p className="text-[11px] text-purple-900/80 leading-relaxed">
                  <span className="font-semibold">Note:</span> "{requirement.reviewer_notes}"
                </p>
              ) : (
                <p className="text-[11px] text-purple-600 italic">No reviewer override applied yet.</p>
              )}
            </div>

            {/* Box 3: Final Assessment */}
            <div className="p-3.5 bg-emerald-50/70 border border-emerald-200 rounded-xl space-y-2">
              <div className="flex items-center gap-1.5 text-emerald-900 font-bold text-xs uppercase tracking-wider">
                <ShieldCheck className="w-4 h-4 text-emerald-700" />
                3. Final Assessment
              </div>
              <div className="pt-1">
                <FinalAssessmentBadge
                  isComplete={requirement.is_final_complete}
                  effectiveStatus={requirement.effective_status}
                  size="sm"
                />
              </div>
              <p className="text-[11px] text-emerald-800 leading-relaxed">
                {requirement.is_final_complete
                  ? 'Counts toward deterministic mandatory completeness (100% complete for this criterion).'
                  : 'Incomplete criterion. Excluded from completion percentage until evidence is confirmed.'}
              </p>
            </div>
          </div>

          {/* AI Evidence & Citation Display */}
          <div className="p-4 bg-slate-50 border border-slate-200 rounded-xl space-y-2">
            <div className="flex items-center justify-between text-xs font-semibold text-slate-700">
              <span className="flex items-center gap-1.5">
                <Quote className="w-3.5 h-3.5 text-slate-400" />
                Application Evidence Citation (Original AI Result)
              </span>
              <span className="text-[11px] text-slate-500 font-normal">
                {requirement.evidence_page ? `Page ${requirement.evidence_page}` : 'No page cited'}
                {requirement.evidence_section ? ` • ${requirement.evidence_section}` : ''}
              </span>
            </div>
            <p className="text-xs italic text-slate-800 bg-white p-3 rounded-lg border border-slate-200/80">
              {requirement.evidence ? `"${requirement.evidence}"` : 'No supporting evidence found in draft application.'}
            </p>
          </div>

          {/* Reviewer Action Tabs */}
          <div className="space-y-4 pt-2">
            <div className="flex items-center justify-between border-b border-slate-200 pb-2">
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-700">
                Select Human Review Action
              </h3>
              <div className="flex items-center gap-1 bg-slate-100 p-1 rounded-lg">
                <button
                  type="button"
                  onClick={() => setActiveTab('confirm')}
                  className={`px-3 py-1 text-xs font-bold rounded-md transition-colors ${
                    activeTab === 'confirm'
                      ? 'bg-teal-600 text-white shadow-xs'
                      : 'text-slate-600 hover:text-slate-900'
                  }`}
                >
                  Confirm
                </button>
                <button
                  type="button"
                  onClick={() => setActiveTab('correct')}
                  className={`px-3 py-1 text-xs font-bold rounded-md transition-colors ${
                    activeTab === 'correct'
                      ? 'bg-blue-600 text-white shadow-xs'
                      : 'text-slate-600 hover:text-slate-900'
                  }`}
                >
                  Correct
                </button>
                <button
                  type="button"
                  onClick={() => setActiveTab('reject')}
                  className={`px-3 py-1 text-xs font-bold rounded-md transition-colors ${
                    activeTab === 'reject'
                      ? 'bg-rose-600 text-white shadow-xs'
                      : 'text-slate-600 hover:text-slate-900'
                  }`}
                >
                  Reject
                </button>
              </div>
            </div>

            {errorMsg && (
              <div className="p-3 bg-rose-50 border border-rose-200 text-rose-800 text-xs rounded-lg flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 shrink-0 text-rose-600" />
                <span>{errorMsg}</span>
              </div>
            )}

            {/* TAB 1: CONFIRM */}
            {activeTab === 'confirm' && (
              <div className="p-4 bg-teal-50/50 border border-teal-200 rounded-xl space-y-3">
                <div className="flex items-center gap-2 text-teal-900 text-xs font-bold">
                  <CheckCheck className="w-4 h-4 text-teal-600" />
                  Confirm Requirement Compliance
                </div>
                <p className="text-xs text-teal-800">
                  Accept this mapping. The requirement will be marked as <strong>Reviewer-Confirmed</strong> and count as <strong>Complete</strong> in the deterministic checklist score.
                </p>
                <div>
                  <label className="block text-[11px] font-semibold text-slate-700 uppercase mb-1">
                    Reviewer Notes (Optional)
                  </label>
                  <input
                    type="text"
                    placeholder="e.g. Verified registration number directly with Companies House."
                    value={notes}
                    onChange={(e) => setNotes(e.target.value)}
                    className="w-full text-xs px-3 py-2 bg-white border border-slate-300 rounded-lg focus:ring-1 focus:ring-teal-500"
                  />
                </div>
              </div>
            )}

            {/* TAB 2: CORRECT */}
            {activeTab === 'correct' && (
              <div className="p-4 bg-blue-50/50 border border-blue-200 rounded-xl space-y-3">
                <div className="flex items-center gap-2 text-blue-900 text-xs font-bold">
                  <Edit3 className="w-4 h-4 text-blue-600" />
                  Correct Mapping & Status Override
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div>
                    <label className="block text-[11px] font-semibold text-slate-700 uppercase mb-1">
                      Override Status
                    </label>
                    <select
                      value={overrideStatus}
                      onChange={(e) => setOverrideStatus(e.target.value as MappingStatus)}
                      className="w-full text-xs px-3 py-2 bg-white border border-slate-300 rounded-lg focus:ring-1 focus:ring-blue-500"
                    >
                      <option value="SUPPORTED">SUPPORTED (Complete)</option>
                      <option value="WEAK">WEAK EVIDENCE (Incomplete)</option>
                      <option value="MISSING">MISSING EVIDENCE (Incomplete)</option>
                      <option value="AMBIGUOUS">AMBIGUOUS (Incomplete)</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-[11px] font-semibold text-slate-700 uppercase mb-1">
                      Reviewer Reason / Note (Mandatory)
                    </label>
                    <input
                      type="text"
                      placeholder="Explain the correction rationale..."
                      value={notes}
                      onChange={(e) => setNotes(e.target.value)}
                      required
                      className="w-full text-xs px-3 py-2 bg-white border border-slate-300 rounded-lg focus:ring-1 focus:ring-blue-500"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-[11px] font-semibold text-slate-700 uppercase mb-1">
                    Corrected Evidence / Excerpt (Optional)
                  </label>
                  <textarea
                    rows={2}
                    placeholder="Paste or correct the exact application excerpt..."
                    value={overrideEvidence}
                    onChange={(e) => setOverrideEvidence(e.target.value)}
                    className="w-full text-xs px-3 py-2 bg-white border border-slate-300 rounded-lg focus:ring-1 focus:ring-blue-500"
                  />
                </div>
              </div>
            )}

            {/* TAB 3: REJECT */}
            {activeTab === 'reject' && (
              <div className="p-4 bg-rose-50/50 border border-rose-200 rounded-xl space-y-3">
                <div className="flex items-center gap-2 text-rose-900 text-xs font-bold">
                  <Ban className="w-4 h-4 text-rose-600" />
                  Reject Requirement Mapping
                </div>
                <p className="text-xs text-rose-800">
                  Reject this mapping. The requirement will be marked as <strong>Rejected</strong> and treated as <strong>Incomplete (MISSING)</strong> in the final deterministic score.
                </p>
                <div>
                  <label className="block text-[11px] font-semibold text-slate-700 uppercase mb-1">
                    Reviewer Note Explaining Rejection (Mandatory)
                  </label>
                  <input
                    type="text"
                    placeholder="e.g. Partner letter is unsigned and lacks formal commitment."
                    value={notes}
                    onChange={(e) => setNotes(e.target.value)}
                    required
                    className="w-full text-xs px-3 py-2 bg-white border border-slate-300 rounded-lg focus:ring-1 focus:ring-rose-500"
                  />
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Modal Footer */}
        <div className="px-6 py-4 border-t border-slate-100 bg-slate-50 flex items-center justify-between">
          <div className="flex items-center gap-2 text-xs">
            <span className="font-semibold text-slate-600">Expected Final Result:</span>
            <FinalAssessmentBadge
              isComplete={previewIsComplete}
              effectiveStatus={previewEffectiveStatus}
              size="sm"
            />
          </div>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-xs font-semibold text-slate-600 hover:text-slate-800 bg-white border border-slate-300 rounded-lg hover:bg-slate-50 transition-colors"
            >
              Cancel
            </button>

            {activeTab === 'confirm' && (
              <button
                type="button"
                onClick={() => handleAction('CONFIRMED')}
                disabled={submitting}
                className="inline-flex items-center gap-1.5 px-5 py-2 text-xs font-bold text-white bg-teal-600 hover:bg-teal-700 rounded-lg shadow-xs transition-colors"
              >
                {submitting ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <CheckCheck className="w-3.5 h-3.5" />}
                Confirm Mapping
              </button>
            )}

            {activeTab === 'correct' && (
              <button
                type="button"
                onClick={() => handleAction('CORRECTED')}
                disabled={submitting || !notes.trim()}
                className="inline-flex items-center gap-1.5 px-5 py-2 text-xs font-bold text-white bg-blue-600 hover:bg-blue-700 rounded-lg shadow-xs transition-colors disabled:bg-slate-300"
              >
                {submitting ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Edit3 className="w-3.5 h-3.5" />}
                Apply Correction
              </button>
            )}

            {activeTab === 'reject' && (
              <button
                type="button"
                onClick={() => handleAction('REJECTED')}
                disabled={submitting || !notes.trim()}
                className="inline-flex items-center gap-1.5 px-5 py-2 text-xs font-bold text-white bg-rose-600 hover:bg-rose-700 rounded-lg shadow-xs transition-colors disabled:bg-slate-300"
              >
                {submitting ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Ban className="w-3.5 h-3.5" />}
                Reject Mapping
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
