import React, { useState, useEffect } from 'react';
import { api } from '../api/client';
import { SupportingDocument } from '../types';
import { DisclaimerBanner } from '../components/DisclaimerBanner';
import {
  FileCheck2,
  Plus,
  Trash2,
  CheckCircle2,
  XCircle,
  FileText,
  Save,
  ArrowLeft,
  ArrowRight,
  Loader2,
} from 'lucide-react';

interface Props {
  assessmentId: string;
  onNavigate: (tab: 'dashboard' | 'supporting' | 'summary') => void;
}

export const SupportingDocsPage: React.FC<Props> = ({ assessmentId, onNavigate }) => {
  const [docs, setDocs] = useState<SupportingDocument[]>([]);
  const [loading, setLoading] = useState(true);
  const [savingId, setSavingId] = useState<string | null>(null);

  const [showAddForm, setShowAddForm] = useState(false);
  const [newDocName, setNewDocName] = useState('');
  const [newDocRequired, setNewDocRequired] = useState(true);
  const [newDocNotes, setNewDocNotes] = useState('');
  const [adding, setAdding] = useState(false);

  const [notesBuffer, setNotesBuffer] = useState<Record<string, string>>({});

  const loadDocs = async () => {
    try {
      setLoading(true);
      const res = await api.getSupportingDocs(assessmentId);
      setDocs(res);
      const initialNotes: Record<string, string> = {};
      res.forEach((d) => {
        initialNotes[d.id] = d.reviewer_notes || '';
      });
      setNotesBuffer(initialNotes);
    } catch (err) {
      console.error('Failed to load supporting documents:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDocs();
  }, [assessmentId]);

  const handleToggleSupplied = async (doc: SupportingDocument) => {
    setSavingId(doc.id);
    try {
      const updated = await api.updateSupportingDoc(assessmentId, doc.id, {
        is_supplied: !doc.is_supplied,
      });
      setDocs(docs.map((d) => (d.id === doc.id ? updated : d)));
    } catch (err) {
      console.error('Failed to update supplied status:', err);
    } finally {
      setSavingId(null);
    }
  };

  const handleSaveNotes = async (doc: SupportingDocument) => {
    setSavingId(doc.id);
    try {
      const updated = await api.updateSupportingDoc(assessmentId, doc.id, {
        reviewer_notes: notesBuffer[doc.id] || '',
      });
      setDocs(docs.map((d) => (d.id === doc.id ? updated : d)));
    } catch (err) {
      console.error('Failed to update notes:', err);
    } finally {
      setSavingId(null);
    }
  };

  const handleCreateDoc = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newDocName.trim()) return;

    setAdding(true);
    try {
      const created = await api.addSupportingDoc(assessmentId, {
        name: newDocName.trim(),
        is_required: newDocRequired,
        is_supplied: false,
        reviewer_notes: newDocNotes.trim() || undefined,
      });
      setDocs([...docs, created]);
      setNotesBuffer({ ...notesBuffer, [created.id]: created.reviewer_notes || '' });
      setNewDocName('');
      setNewDocNotes('');
      setShowAddForm(false);
    } catch (err) {
      console.error('Failed to create supporting doc:', err);
    } finally {
      setAdding(false);
    }
  };

  const mandatoryDocs = docs.filter((d) => d.is_required);
  const mandatorySupplied = mandatoryDocs.filter((d) => d.is_supplied).length;

  return (
    <div className="max-w-5xl mx-auto py-6 px-4 sm:px-6 space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <button
            onClick={() => onNavigate('dashboard')}
            className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-500 hover:text-slate-800 mb-2 transition-colors"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            Back to Assessment Dashboard
          </button>
          <h1 className="text-xl font-bold text-slate-900">Supporting Documents Checklist</h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Audit and track mandatory attachments, financial statements, and supporting materials.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowAddForm(true)}
            className="inline-flex items-center gap-1.5 px-3 py-2 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded-lg shadow-xs transition-colors"
          >
            <Plus className="w-3.5 h-3.5" />
            Add Required Document
          </button>
          <button
            onClick={() => onNavigate('summary')}
            className="inline-flex items-center gap-1.5 px-3 py-2 text-xs font-semibold text-slate-700 bg-white border border-slate-300 hover:bg-slate-50 rounded-lg shadow-xs transition-colors"
          >
            Review Summary
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      <DisclaimerBanner />

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-xs">
          <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
            Total Tracked Documents
          </span>
          <p className="text-2xl font-black text-slate-900 mt-1">{docs.length}</p>
          <p className="text-xs text-slate-500 mt-0.5">across mandatory & optional attachments</p>
        </div>

        <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-xs">
          <span className="text-xs font-semibold text-emerald-700 uppercase tracking-wider">
            Mandatory Documents Supplied
          </span>
          <p className="text-2xl font-black text-emerald-700 mt-1">
            {mandatorySupplied} / {mandatoryDocs.length}
          </p>
          <div className="w-full bg-slate-100 h-1.5 rounded-full overflow-hidden mt-2">
            <div
              className="bg-emerald-600 h-1.5 rounded-full"
              style={{
                width: `${mandatoryDocs.length > 0 ? (mandatorySupplied / mandatoryDocs.length) * 100 : 100}%`,
              }}
            ></div>
          </div>
        </div>

        <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-xs">
          <span className="text-xs font-semibold text-rose-700 uppercase tracking-wider">
            Missing Mandatory Documents
          </span>
          <p className="text-2xl font-black text-rose-700 mt-1">
            {mandatoryDocs.length - mandatorySupplied}
          </p>
          <p className="text-xs text-rose-600 mt-0.5">must be supplied before final grant submission</p>
        </div>
      </div>

      {showAddForm && (
        <form
          onSubmit={handleCreateDoc}
          className="bg-white border-2 border-blue-200 rounded-xl p-5 shadow-xs space-y-4"
        >
          <div className="flex items-center justify-between border-b border-slate-100 pb-2">
            <h3 className="text-sm font-bold text-slate-900">Add Supporting Document Requirement</h3>
            <button
              type="button"
              onClick={() => setShowAddForm(false)}
              className="text-xs text-slate-400 hover:text-slate-600"
            >
              Cancel
            </button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">
                Document Name / Title
              </label>
              <input
                type="text"
                placeholder="e.g. Consortium Agreement, Audit Report 2025"
                value={newDocName}
                onChange={(e) => setNewDocName(e.target.value)}
                required
                className="w-full px-3 py-1.5 text-xs border border-slate-300 rounded focus:ring-1 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">
                Reviewer Instructions / Notes
              </label>
              <input
                type="text"
                placeholder="e.g. Needs to be signed by all participating partners"
                value={newDocNotes}
                onChange={(e) => setNewDocNotes(e.target.value)}
                className="w-full px-3 py-1.5 text-xs border border-slate-300 rounded focus:ring-1 focus:ring-blue-500"
              />
            </div>
          </div>

          <div className="flex items-center justify-between pt-2">
            <label className="flex items-center gap-2 text-xs font-medium text-slate-700 cursor-pointer">
              <input
                type="checkbox"
                checked={newDocRequired}
                onChange={(e) => setNewDocRequired(e.target.checked)}
                className="rounded border-slate-300 text-blue-600 focus:ring-blue-500"
              />
              Mandatory attachment for submission
            </label>

            <button
              type="submit"
              disabled={adding || !newDocName.trim()}
              className="px-4 py-1.5 bg-blue-600 text-white rounded text-xs font-semibold hover:bg-blue-700 disabled:bg-slate-300"
            >
              {adding ? 'Saving...' : 'Add Document'}
            </button>
          </div>
        </form>
      )}

      <div className="bg-white border border-slate-200 rounded-xl shadow-xs overflow-hidden">
        <div className="px-5 py-3 border-b border-slate-200 bg-slate-50 flex items-center justify-between">
          <h2 className="text-xs font-bold uppercase tracking-wider text-slate-700">
            Tracked Documents ({docs.length})
          </h2>
          <span className="text-[11px] text-slate-500">
            Toggle status to mark as verified supplied or missing
          </span>
        </div>

        {docs.length === 0 ? (
          <div className="p-8 text-center text-slate-500 text-xs">
            No supporting documents recorded for this assessment.
          </div>
        ) : (
          <div className="divide-y divide-slate-100">
            {docs.map((doc) => {
              const isSaving = savingId === doc.id;
              const hasUnsavedNotes = (notesBuffer[doc.id] ?? '') !== (doc.reviewer_notes ?? '');

              return (
                <div key={doc.id} className="p-5 flex flex-col md:flex-row gap-4 items-start justify-between">
                  <div className="space-y-2 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="text-sm font-semibold text-slate-900">{doc.name}</span>
                      {doc.is_required ? (
                        <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-rose-50 text-rose-700 border border-rose-200">
                          MANDATORY
                        </span>
                      ) : (
                        <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-slate-100 text-slate-600">
                          OPTIONAL
                        </span>
                      )}

                      {doc.is_supplied ? (
                        <span className="inline-flex items-center gap-1 text-[10px] font-bold px-2 py-0.5 rounded bg-emerald-50 text-emerald-700 border border-emerald-200">
                          <CheckCircle2 className="w-3 h-3 text-emerald-600" />
                          SUPPLIED
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 text-[10px] font-bold px-2 py-0.5 rounded bg-rose-50 text-rose-700 border border-rose-200">
                          <XCircle className="w-3 h-3 text-rose-600" />
                          NOT SUPPLIED
                        </span>
                      )}
                    </div>

                    {doc.filename && (
                      <p className="text-xs text-slate-500">
                        Linked file: <span className="font-mono text-slate-700">{doc.filename}</span>
                      </p>
                    )}

                    <div className="pt-1">
                      <label className="block text-[11px] font-semibold text-slate-500 uppercase mb-1">
                        Reviewer Notes:
                      </label>
                      <div className="flex items-center gap-2">
                        <input
                          type="text"
                          value={notesBuffer[doc.id] ?? ''}
                          onChange={(e) =>
                            setNotesBuffer({ ...notesBuffer, [doc.id]: e.target.value })
                          }
                          placeholder="Add comments on document completeness, validity dates, etc."
                          className="w-full text-xs px-2.5 py-1.5 border border-slate-300 rounded focus:ring-1 focus:ring-blue-500"
                        />
                        {hasUnsavedNotes && (
                          <button
                            onClick={() => handleSaveNotes(doc)}
                            disabled={isSaving}
                            className="inline-flex items-center gap-1 px-2.5 py-1.5 text-xs font-semibold bg-blue-600 text-white rounded hover:bg-blue-700 shrink-0"
                          >
                            <Save className="w-3 h-3" />
                            Save
                          </button>
                        )}
                      </div>
                    </div>
                  </div>

                  <div className="shrink-0 flex items-center gap-2 pt-1">
                    <button
                      onClick={() => handleToggleSupplied(doc)}
                      disabled={isSaving}
                      className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold border transition-colors ${
                        doc.is_supplied
                          ? 'border-emerald-300 bg-emerald-50 text-emerald-800 hover:bg-emerald-100'
                          : 'border-slate-300 bg-white text-slate-700 hover:bg-slate-50'
                      }`}
                    >
                      {isSaving ? (
                        <Loader2 className="w-3.5 h-3.5 animate-spin" />
                      ) : doc.is_supplied ? (
                        <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                      ) : (
                        <XCircle className="w-3.5 h-3.5 text-slate-400" />
                      )}
                      {doc.is_supplied ? 'Mark as Not Supplied' : 'Mark as Supplied'}
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};
