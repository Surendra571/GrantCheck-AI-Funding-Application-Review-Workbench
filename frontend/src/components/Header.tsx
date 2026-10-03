import React from 'react';
import { FileCheck2, PlusCircle, LayoutDashboard, FileText } from 'lucide-react';

interface Props {
  activeTab?: string;
  setActiveTab?: (tab: string) => void;
  assessmentId?: string | null;
  assessmentTitle?: string;
  onNavigateHome?: () => void;
  onNavigateNew?: () => void;
}

export const Header: React.FC<Props> = ({
  activeTab = 'dashboard',
  setActiveTab,
  assessmentId,
  onNavigateHome,
  onNavigateNew,
}) => {
  return (
    <header className="bg-white border-b border-slate-200 sticky top-0 z-30 shadow-xs">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          <div className="flex items-center gap-3 cursor-pointer" onClick={onNavigateHome}>
            <div className="p-2 bg-blue-600 rounded-lg text-white shadow-xs">
              <FileCheck2 className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-black text-slate-900 text-lg tracking-tight">GrantCheck</span>
                <span className="text-[10px] uppercase font-bold bg-blue-50 text-blue-700 px-2 py-0.5 rounded-full border border-blue-200">
                  Review Workbench
                </span>
              </div>
              <p className="text-[11px] text-slate-500 font-medium">
                AI-Assisted Completeness & Evidence Auditor
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            {assessmentId && setActiveTab && (
              <nav className="hidden md:flex items-center gap-1 bg-slate-100 p-1 rounded-lg">
                <button
                  onClick={() => setActiveTab('dashboard')}
                  className={`px-3 py-1.5 text-xs font-semibold rounded-md transition-colors ${
                    activeTab === 'dashboard'
                      ? 'bg-white text-slate-900 shadow-xs'
                      : 'text-slate-600 hover:text-slate-900'
                  }`}
                >
                  <span className="flex items-center gap-1.5">
                    <LayoutDashboard className="w-3.5 h-3.5" />
                    Dashboard
                  </span>
                </button>
                <button
                  onClick={() => setActiveTab('supporting')}
                  className={`px-3 py-1.5 text-xs font-semibold rounded-md transition-colors ${
                    activeTab === 'supporting'
                      ? 'bg-white text-slate-900 shadow-xs'
                      : 'text-slate-600 hover:text-slate-900'
                  }`}
                >
                  <span className="flex items-center gap-1.5">
                    <FileText className="w-3.5 h-3.5" />
                    Supporting Docs
                  </span>
                </button>
                <button
                  onClick={() => setActiveTab('summary')}
                  className={`px-3 py-1.5 text-xs font-semibold rounded-md transition-colors ${
                    activeTab === 'summary'
                      ? 'bg-white text-slate-900 shadow-xs'
                      : 'text-slate-600 hover:text-slate-900'
                  }`}
                >
                  <span className="flex items-center gap-1.5">
                    <FileCheck2 className="w-3.5 h-3.5" />
                    Reviewed Summary
                  </span>
                </button>
              </nav>
            )}

            {onNavigateNew && (
              <button
                onClick={onNavigateNew}
                className="inline-flex items-center gap-1.5 px-3 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-xs font-semibold shadow-xs transition-colors"
              >
                <PlusCircle className="w-3.5 h-3.5" />
                New Assessment
              </button>
            )}
          </div>
        </div>
      </div>
    </header>
  );
};
