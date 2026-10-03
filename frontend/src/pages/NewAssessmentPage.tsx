import React, { useState } from 'react';
import { api } from '../api/client';
import { DisclaimerBanner } from '../components/DisclaimerBanner';
import { FileUp, Plus, Trash2, ArrowRight, Loader2, CheckCircle2, AlertCircle } from 'lucide-react';

interface Props {
  onAssessmentCreated: (id: string) => void;
  onCancel?: () => void;
}

interface SupportingDocDraft {
  name: string;
  is_required: boolean;
  notes: string;
}

export const NewAssessmentPage: React.FC<Props> = ({ onAssessmentCreated }) => {
  const [title, setTitle] = useState('');
  const [grantName, setGrantName] = useState('');
  const [applicationName, setApplicationName] = useState('');
  const [guidelineFile, setGuidelineFile] = useState<File | null>(null);
  const [applicationFile, setApplicationFile] = useState<File | null>(null);
  const [supportingDocs, setSupportingDocs] = useState<SupportingDocDraft[]>([
    { name: 'Audited Financial Statements (Last 2 Years)', is_required: true, notes: '' },
    { name: 'Key Personnel CVs & Credentials', is_required: true, notes: '' },
  ]);

  const [loading, setLoading] = useState(false);
  const [stepMessage, setStepMessage] = useState('');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const handleAddSupportingDoc = () => {
    setSupportingDocs([...supportingDocs, { name: '', is_required: true, notes: '' }]);
  };

  const handleRemoveSupportingDoc = (idx: number) => {
    setSupportingDocs(supportingDocs.filter((_, i) => i !== idx));
  };

  const handleSupportingDocChange = (idx: number, field: keyof SupportingDocDraft, value: any) => {
    const updated = [...supportingDocs];
    updated[idx] = { ...updated[idx], [field]: value };
    setSupportingDocs(updated);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!guidelineFile || !applicationFile) {
      setErrorMessage('Please upload both a Grant Guideline document and a Draft Application document.');
      return;
    }

    setLoading(true);
    setErrorMessage(null);

    try {
      const gName = grantName.trim() || guidelineFile.name.replace(/\.[^/.]+$/, '');
      const aName = applicationName.trim() || applicationFile.name.replace(/\.[^/.]+$/, '');
      const docTitle = title.trim() || `${aName} vs ${gName}`;

      setStepMessage('Creating assessment record...');
      const assessment = await api.createAssessment({
        title: docTitle,
        grant_name: gName,
        application_name: aName,
      });

      setStepMessage('Uploading Grant Guideline document...');
      await api.uploadDocument(assessment.id, 'guideline', guidelineFile);

      setStepMessage('Uploading Draft Application document...');
      await api.uploadDocument(assessment.id, 'application', applicationFile);

      for (const doc of supportingDocs) {
        if (doc.name.trim()) {
          await api.addSupportingDoc(assessment.id, {
            name: doc.name.trim(),
            is_required: doc.is_required,
            is_supplied: false,
            reviewer_notes: doc.notes.trim() || undefined,
          });
        }
      }

      setStepMessage('Running 8-step controlled AI review pipeline (extraction, evidence retrieval, mapping, gap & claim detection)...');
      await api.analyzeAssessment(assessment.id);

      setStepMessage('Analysis complete! Redirecting to review workbench...');
      setTimeout(() => {
        onAssessmentCreated(assessment.id);
      }, 500);
    } catch (err: any) {
      console.error('Assessment creation error:', err);
      setErrorMessage(err.message || 'An error occurred during assessment creation and analysis.');
      setLoading(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto py-8 px-4 sm:px-6">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Create New Assessment</h1>
        <p className="text-sm text-slate-600 mt-1">
          Upload your funding guideline and draft application to initiate the automated completeness and evidence review.
        </p>
      </div>

      <DisclaimerBanner className="mb-6" />

      {errorMessage && (
        <div className="mb-6 p-4 bg-rose-50 border border-rose-200 rounded-lg flex items-start gap-3 text-rose-800">
          <AlertCircle className="w-5 h-5 text-rose-600 mt-0.5 shrink-0" />
          <div>
            <h4 className="font-semibold text-sm">Review Initialization Failed</h4>
            <p className="text-xs mt-0.5">{errorMessage}</p>
          </div>
        </div>
      )}

      {loading ? (
        <div className="bg-white border border-slate-200 rounded-xl p-10 text-center shadow-xs">
          <div className="inline-flex p-4 rounded-full bg-blue-50 text-blue-600 mb-4 animate-pulse">
            <Loader2 className="w-8 h-8 animate-spin" />
          </div>
          <h3 className="text-lg font-semibold text-slate-900 mb-2">Analyzing Application Materials</h3>
          <p className="text-sm text-slate-600 max-w-md mx-auto mb-6">{stepMessage}</p>
          
          <div className="max-w-md mx-auto bg-slate-100 rounded-full h-2 overflow-hidden mb-4">
            <div className="bg-blue-600 h-2 rounded-full animate-pulse w-3/4"></div>
          </div>
          
          <div className="text-xs text-slate-500 space-y-1">
            <p>1. Document Parsing & Section Extraction</p>
            <p>2. Guideline Structured Requirements Extraction</p>
            <p>3. Application Evidence Retrieval & Anti-Hallucination Verification</p>
            <p>4. Deterministic Scoring & Gap Clarifications</p>
          </div>
        </div>
      ) : (
        <form onSubmit={handleSubmit} className="space-y-6">
          <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-xs space-y-4">
            <h2 className="text-base font-semibold text-slate-900 border-b border-slate-100 pb-3">
              Assessment Metadata
            </h2>
            <div className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1.5">
                  Assessment Title (Optional)
                </label>
                <input
                  type="text"
                  placeholder="e.g. Innovate UK 2026 - Q2 Submission Review"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  className="w-full px-3 py-2 text-sm border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-600"
                />
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1.5">
                    Grant Program / Guideline Name
                  </label>
                  <input
                    type="text"
                    placeholder="e.g. Innovate UK Smart Grant 2026"
                    value={grantName}
                    onChange={(e) => setGrantName(e.target.value)}
                    className="w-full px-3 py-2 text-sm border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-600"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1.5">
                    Draft Application / Proposal Title
                  </label>
                  <input
                    type="text"
                    placeholder="e.g. NextGen Clean Energy Storage Proposal"
                    value={applicationName}
                    onChange={(e) => setApplicationName(e.target.value)}
                    className="w-full px-3 py-2 text-sm border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-600"
                  />
                </div>
              </div>
            </div>
          </div>

          <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-xs space-y-4">
            <h2 className="text-base font-semibold text-slate-900 border-b border-slate-100 pb-3">
              Source Documents (Mandatory)
            </h2>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="border-2 border-dashed border-slate-200 rounded-lg p-5 hover:border-blue-400 transition-colors">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-bold uppercase tracking-wider text-slate-700">
                    Grant Guideline Document
                  </span>
                  <span className="text-[11px] font-medium text-blue-700 bg-blue-50 px-2 py-0.5 rounded">
                    PDF, DOCX, TXT, MD
                  </span>
                </div>
                <p className="text-xs text-slate-500 mb-4">
                  The official solicitation, guidelines, or notice of funding opportunity.
                </p>
                
                <input
                  type="file"
                  id="guideline-file-input"
                  accept=".pdf,.docx,.txt,.md"
                  onChange={(e) => e.target.files?.[0] && setGuidelineFile(e.target.files[0])}
                  className="hidden"
                />
                
                {guidelineFile ? (
                  <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-lg flex items-center justify-between">
                    <div className="flex items-center gap-2 truncate">
                      <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                      <span className="text-xs font-medium text-emerald-900 truncate">
                        {guidelineFile.name}
                      </span>
                      <span className="text-[11px] text-emerald-700">
                        ({(guidelineFile.size / 1024).toFixed(1)} KB)
                      </span>
                    </div>
                    <label
                      htmlFor="guideline-file-input"
                      className="text-xs text-emerald-800 underline cursor-pointer hover:text-emerald-950 ml-2"
                    >
                      Change
                    </label>
                  </div>
                ) : (
                  <label
                    htmlFor="guideline-file-input"
                    className="flex flex-col items-center justify-center p-4 bg-slate-50 rounded-lg cursor-pointer hover:bg-slate-100 transition-colors text-slate-600"
                  >
                    <FileUp className="w-6 h-6 text-slate-400 mb-1" />
                    <span className="text-xs font-semibold text-slate-700">Click to upload guideline</span>
                    <span className="text-[11px] text-slate-500">Max size 25MB</span>
                  </label>
                )}
              </div>

              <div className="border-2 border-dashed border-slate-200 rounded-lg p-5 hover:border-blue-400 transition-colors">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-bold uppercase tracking-wider text-slate-700">
                    Draft Application Document
                  </span>
                  <span className="text-[11px] font-medium text-blue-700 bg-blue-50 px-2 py-0.5 rounded">
                    PDF, DOCX, TXT, MD
                  </span>
                </div>
                <p className="text-xs text-slate-500 mb-4">
                  The applicant's draft proposal narrative, budget description, or project summary.
                </p>

                <input
                  type="file"
                  id="application-file-input"
                  accept=".pdf,.docx,.txt,.md"
                  onChange={(e) => e.target.files?.[0] && setApplicationFile(e.target.files[0])}
                  className="hidden"
                />

                {applicationFile ? (
                  <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-lg flex items-center justify-between">
                    <div className="flex items-center gap-2 truncate">
                      <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                      <span className="text-xs font-medium text-emerald-900 truncate">
                        {applicationFile.name}
                      </span>
                      <span className="text-[11px] text-emerald-700">
                        ({(applicationFile.size / 1024).toFixed(1)} KB)
                      </span>
                    </div>
                    <label
                      htmlFor="application-file-input"
                      className="text-xs text-emerald-800 underline cursor-pointer hover:text-emerald-950 ml-2"
                    >
                      Change
                    </label>
                  </div>
                ) : (
                  <label
                    htmlFor="application-file-input"
                    className="flex flex-col items-center justify-center p-4 bg-slate-50 rounded-lg cursor-pointer hover:bg-slate-100 transition-colors text-slate-600"
                  >
                    <FileUp className="w-6 h-6 text-slate-400 mb-1" />
                    <span className="text-xs font-semibold text-slate-700">Click to upload application</span>
                    <span className="text-[11px] text-slate-500">Max size 25MB</span>
                  </label>
                )}
              </div>
            </div>
          </div>

          <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-xs space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div>
                <h2 className="text-base font-semibold text-slate-900">
                  Supporting Document Checklist (Optional)
                </h2>
                <p className="text-xs text-slate-500 mt-0.5">
                  Track required attachments like financial statements, CVs, letters of support, or certificates.
                </p>
              </div>
              <button
                type="button"
                onClick={handleAddSupportingDoc}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-blue-700 bg-blue-50 hover:bg-blue-100 rounded-lg transition-colors"
              >
                <Plus className="w-3.5 h-3.5" />
                Add Item
              </button>
            </div>

            <div className="space-y-3">
              {supportingDocs.map((doc, idx) => (
                <div key={idx} className="flex items-center gap-3 p-3 bg-slate-50 border border-slate-200 rounded-lg">
                  <div className="flex-1">
                    <input
                      type="text"
                      placeholder="e.g. Letter of Commitment"
                      value={doc.name}
                      onChange={(e) => handleSupportingDocChange(idx, 'name', e.target.value)}
                      className="w-full px-3 py-1.5 text-xs bg-white border border-slate-300 rounded focus:outline-none focus:ring-1 focus:ring-blue-500"
                    />
                  </div>
                  <label className="flex items-center gap-1.5 cursor-pointer text-xs font-medium text-slate-700 shrink-0">
                    <input
                      type="checkbox"
                      checked={doc.is_required}
                      onChange={(e) => handleSupportingDocChange(idx, 'is_required', e.target.checked)}
                      className="rounded border-slate-300 text-blue-600 focus:ring-blue-500"
                    />
                    Mandatory
                  </label>
                  <button
                    type="button"
                    onClick={() => handleRemoveSupportingDoc(idx)}
                    className="p-1.5 text-slate-400 hover:text-rose-600 transition-colors"
                    title="Remove"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              ))}
            </div>
          </div>

          <div className="flex items-center justify-end gap-3 pt-2">
            <button
              type="submit"
              disabled={!guidelineFile || !applicationFile || loading}
              className={`inline-flex items-center gap-2 px-6 py-2.5 rounded-lg text-sm font-semibold shadow-xs transition-all ${
                guidelineFile && applicationFile && !loading
                  ? 'bg-blue-600 hover:bg-blue-700 text-white shadow-blue-500/20'
                  : 'bg-slate-200 text-slate-400 cursor-not-allowed'
              }`}
            >
              Analyze Application
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        </form>
      )}
    </div>
  );
};
