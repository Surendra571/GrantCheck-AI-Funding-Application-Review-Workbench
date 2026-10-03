import React from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';

interface Props {
  reason?: string | null;
  onReanalyze?: () => void;
  isAnalyzing?: boolean;
}

export const StaleWarningBanner: React.FC<Props> = ({ reason, onReanalyze, isAnalyzing }) => {
  return (
    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-4 bg-amber-50 border-2 border-amber-300 rounded-xl text-amber-950 shadow-sm">
      <div className="flex items-start gap-3">
        <div className="p-2 bg-amber-100 rounded-lg text-amber-700 shrink-0 mt-0.5">
          <AlertTriangle className="w-5 h-5" />
        </div>
        <div>
          <h4 className="font-bold text-sm tracking-wide text-amber-900">
            Assessment stale — source document changed.
          </h4>
          <p className="text-xs sm:text-sm text-amber-800 mt-0.5">
            {reason || 'A guideline or application source document has been updated with a new content hash. Re-analysis is required to sync checklist requirements and evidence citations.'}
          </p>
        </div>
      </div>

      {onReanalyze && (
        <button
          onClick={onReanalyze}
          disabled={isAnalyzing}
          className="inline-flex items-center gap-1.5 px-4 py-2 bg-amber-600 hover:bg-amber-700 text-white rounded-lg text-xs font-semibold shadow-xs disabled:bg-slate-300 transition-colors shrink-0"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isAnalyzing ? 'animate-spin' : ''}`} />
          {isAnalyzing ? 'Re-analyzing...' : 'Re-analyze Application'}
        </button>
      )}
    </div>
  );
};
