import React, { useState, useEffect } from 'react';
import { Header } from './components/Header';
import { AssessmentsListPage } from './pages/AssessmentsListPage';
import { NewAssessmentPage } from './pages/NewAssessmentPage';
import { AssessmentDashboardPage } from './pages/AssessmentDashboardPage';
import { SupportingDocsPage } from './pages/SupportingDocsPage';
import { ReviewedSummaryPage } from './pages/ReviewedSummaryPage';

type ViewMode = 'list' | 'new' | 'dashboard' | 'supporting' | 'summary';

export default function App() {
  const [view, setView] = useState<ViewMode>('list');
  const [assessmentId, setAssessmentId] = useState<string | null>(null);

  useEffect(() => {
    const handleHash = () => {
      const hash = window.location.hash.replace(/^#\/?/, '');
      if (!hash) {
        setView('list');
        return;
      }

      const [route, id, sub] = hash.split('/');
      if (route === 'new') {
        setView('new');
        setAssessmentId(null);
      } else if (route === 'assessments' && id) {
        setAssessmentId(id);
        if (sub === 'supporting') {
          setView('supporting');
        } else if (sub === 'summary') {
          setView('summary');
        } else {
          setView('dashboard');
        }
      } else {
        setView('list');
        setAssessmentId(null);
      }
    };

    handleHash();
    window.addEventListener('hashchange', handleHash);
    return () => window.removeEventListener('hashchange', handleHash);
  }, []);

  const navigateTo = (newView: ViewMode, id?: string) => {
    const targetId = id || assessmentId;
    if (newView === 'list') {
      window.location.hash = '#/';
    } else if (newView === 'new') {
      window.location.hash = '#/new';
    } else if (targetId) {
      if (newView === 'supporting') {
        window.location.hash = `#/assessments/${targetId}/supporting`;
      } else if (newView === 'summary') {
        window.location.hash = `#/assessments/${targetId}/summary`;
      } else {
        window.location.hash = `#/assessments/${targetId}`;
      }
    }
  };

  const handleAssessmentCreated = (newId: string) => {
    setAssessmentId(newId);
    navigateTo('dashboard', newId);
  };

  const handleSelectAssessment = (id: string) => {
    setAssessmentId(id);
    navigateTo('dashboard', id);
  };

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col font-sans">
      <Header
        activeTab={
          view === 'list'
            ? 'dashboard'
            : view === 'supporting'
            ? 'supporting'
            : view === 'summary'
            ? 'summary'
            : 'dashboard'
        }
        setActiveTab={(tab: string) => {
          if (tab === 'dashboard' || tab === 'supporting' || tab === 'summary') {
            navigateTo(tab);
          }
        }}
        assessmentId={assessmentId}
        onNavigateHome={() => navigateTo('list')}
        onNavigateNew={() => navigateTo('new')}
      />

      <main className="flex-1 pb-16">
        {view === 'list' && (
          <AssessmentsListPage
            onSelectAssessment={handleSelectAssessment}
            onNewAssessment={() => navigateTo('new')}
          />
        )}

        {view === 'new' && (
          <NewAssessmentPage
            onAssessmentCreated={handleAssessmentCreated}
            onCancel={() => navigateTo('list')}
          />
        )}

        {view === 'dashboard' && assessmentId && (
          <AssessmentDashboardPage
            assessmentId={assessmentId}
            onNavigate={(tab) => navigateTo(tab)}
          />
        )}

        {view === 'supporting' && assessmentId && (
          <SupportingDocsPage
            assessmentId={assessmentId}
            onNavigate={(tab) => navigateTo(tab)}
          />
        )}

        {view === 'summary' && assessmentId && (
          <ReviewedSummaryPage
            assessmentId={assessmentId}
            onNavigate={(tab) => navigateTo(tab)}
          />
        )}
      </main>

      <footer className="py-4 border-t border-slate-200 bg-white text-center text-xs text-slate-500">
        <p>
          GrantCheck AI-Assisted Funding Application Review Workbench &bull; Completeness & Evidence Auditor
        </p>
        <p className="text-[11px] text-slate-400 mt-0.5">
          Notice: Not an authoritative legal, regulatory, or funding-eligibility decision.
        </p>
      </footer>
    </div>
  );
}
