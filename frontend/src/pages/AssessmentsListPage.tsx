import React, { useState, useEffect } from 'react';
import { api } from '../api/client';
import { AssessmentListItem } from '../types';
import { DisclaimerBanner } from '../components/DisclaimerBanner';
import { Plus, ArrowRight, RefreshCw, FileText, AlertTriangle, Layers } from 'lucide-react';

interface Props {
  onSelectAssessment: (id: string) => void;
  onNewAssessment: () => void;
}

export const AssessmentsListPage: React.FC<Props> = ({ onSelectAssessment, onNewAssessment }) => {
  const [assessments, setAssessments] = useState<AssessmentListItem[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchAssessments = async () => {
    try {
      setLoading(true);
      const data = await api.getAssessments();
      setAssessments(data);
    } catch (err) {
      console.error('Failed to list assessments:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAssessments();
  }, []);

  return (
    <div className="max-w-6xl mx-auto py-8 px-4 sm:px-6 space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Review Assessments</h1>
          <p className="text-sm text-slate-600 mt-1">
            Browse, manage, and conduct completeness audits on draft funding applications.
          </p>
        </div>

        <button
          onClick={onNewAssessment}
          className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold rounded-lg shadow-xs transition-all"
        >
          <Plus className="w-4 h-4" />
          Create New Assessment
        </button>
      </div>

      <DisclaimerBanner />

      {loading ? (
        <div className="bg-white border border-slate-200 rounded-xl p-12 text-center text-slate-500">
          <RefreshCw className="w-6 h-6 animate-spin text-blue-600 mx-auto mb-2" />
          <p className="text-xs font-medium">Loading assessments...</p>
        </div>
      ) : assessments.length === 0 ? (
        <div className="bg-white border border-slate-200 rounded-xl p-12 text-center shadow-xs">
          <Layers className="w-10 h-10 text-slate-300 mx-auto mb-3" />
          <h3 className="text-base font-semibold text-slate-800">No assessments created yet</h3>
          <p className="text-xs text-slate-500 max-w-sm mx-auto mt-1 mb-6">
            Upload your first grant guideline and application draft to start the automated completeness review.
          </p>
          <button
            onClick={onNewAssessment}
            className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white text-xs font-semibold rounded-lg hover:bg-blue-700"
          >
            <Plus className="w-4 h-4" />
            Create First Assessment
          </button>
        </div>
      ) : (
        <div className="bg-white border border-slate-200 rounded-xl shadow-xs overflow-hidden">
          <div className="px-6 py-4 border-b border-slate-200 bg-slate-50/70 flex items-center justify-between">
            <h2 className="text-xs font-bold uppercase tracking-wider text-slate-700">
              Active Assessment Portfolio ({assessments.length})
            </h2>
            <button
              onClick={fetchAssessments}
              className="text-xs text-slate-500 hover:text-slate-700 inline-flex items-center gap-1 font-medium"
            >
              <RefreshCw className="w-3 h-3" />
              Refresh
            </button>
          </div>

          <div className="divide-y divide-slate-100">
            {assessments.map((a) => (
              <div
                key={a.id}
                onClick={() => onSelectAssessment(a.id)}
                className="p-5 hover:bg-slate-50 transition-colors flex flex-col md:flex-row items-start md:items-center justify-between gap-4 cursor-pointer"
              >
                <div className="space-y-1.5">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="text-xs font-mono font-bold text-slate-500">
                      {a.id.slice(0, 8)}
                    </span>
                    <span className="text-xs font-bold px-2.5 py-0.5 rounded-full bg-blue-50 text-blue-700 border border-blue-200">
                      {a.status}
                    </span>
                    {a.is_stale && (
                      <span className="inline-flex items-center gap-1 text-[10px] font-bold px-2 py-0.5 rounded bg-amber-100 text-amber-900 border border-amber-300">
                        <AlertTriangle className="w-3 h-3 text-amber-600" />
                        STALE (SOURCE CHANGED)
                      </span>
                    )}
                  </div>

                  <h3 className="text-base font-bold text-slate-900">{a.application_name}</h3>
                  <p className="text-xs text-slate-500">
                    Guideline:{' '}
                    <span className="font-semibold text-slate-700">{a.grant_name}</span>
                  </p>
                </div>

                <div className="flex items-center gap-6 self-end md:self-center">
                  <div className="text-right text-xs text-slate-500">
                    <p>Guideline v{a.guideline_version ?? 1} • App v{a.application_version ?? 1}</p>
                    <p className="text-[11px] text-slate-400 mt-0.5">
                      Created: {new Date(a.created_at).toLocaleDateString()}
                    </p>
                  </div>

                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      onSelectAssessment(a.id);
                    }}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg bg-slate-100 hover:bg-blue-600 hover:text-white text-slate-700 transition-colors"
                  >
                    Open Workbench
                    <ArrowRight className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
