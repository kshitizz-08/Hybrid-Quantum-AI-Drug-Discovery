import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';
import { targetsApi, experimentsApi } from '../api/client';
import type { Target } from '../types';
import { Button } from '../components/ui/Button';

// ── Dataset info constant (matches actual project dataset) ────
const DATASET_INFO = {
  path: 'data/raw/EGFR_bioactivity_raw.csv',
  version: 'chembl_33',
  label: 'EGFR_bioactivity_raw.csv',
  source: 'ChEMBL Database (CHEMBL203)',
  type: 'IC50 Bioactivity Records',
  description: 'Raw bioactivity measurements (IC50, nM) for EGFR inhibitors from ChEMBL.',
};

export const NewDiscoveryPage: React.FC = () => {
  const navigate = useNavigate();
  const { isAuthenticated } = useAuthStore();

  const [targets, setTargets] = useState<Target[]>([]);
  const [targetsLoading, setTargetsLoading] = useState(true);

  const [form, setForm] = useState({
    name: '',
    description: '',
    target_id: '',
  });

  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Guard
  useEffect(() => {
    if (!isAuthenticated) navigate('/login');
  }, [isAuthenticated, navigate]);

  // Load targets from API
  useEffect(() => {
    const load = async () => {
      try {
        const res = await targetsApi.list();
        setTargets(res.data);
        // Auto-select EGFR if present
        const egfr = res.data.find((t: Target) => t.chembl_id === 'CHEMBL203');
        if (egfr) setForm(prev => ({ ...prev, target_id: String(egfr.id) }));
      } catch {
        // Non-critical — user can still create without a target
      } finally {
        setTargetsLoading(false);
      }
    };
    load();
  }, []);

  const selectedTarget = targets.find(t => String(t.id) === form.target_id) ?? null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.name.trim()) {
      setError('Experiment name is required.');
      return;
    }
    setError(null);
    setSubmitting(true);
    try {
      const payload: {
        name: string;
        description?: string;
        target_id?: number;
        dataset_path: string;
        dataset_version: string;
      } = {
        name: form.name.trim(),
        dataset_path: DATASET_INFO.path,
        dataset_version: DATASET_INFO.version,
      };
      if (form.description.trim()) payload.description = form.description.trim();
      if (form.target_id) payload.target_id = parseInt(form.target_id, 10);

      const res = await experimentsApi.create(payload);
      navigate(`/experiments/${res.data.id}`);
    } catch (err: unknown) {
      const axiosErr = err as { response?: { data?: { detail?: string } } };
      const msg = axiosErr?.response?.data?.detail;
      if (typeof msg === 'string') {
        setError(msg);
      } else {
        setError('Failed to create experiment. Please check the backend is running.');
      }
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen pt-16 pl-56">
      <div className="p-8 max-w-3xl">

        {/* Header */}
        <div className="mb-8 animate-slide-up">
          <div className="section-divider mb-3" />
          <h1 className="text-2xl font-bold text-white mb-1">New Discovery Experiment</h1>
          <p className="text-slate-400 text-sm">
            Set up a new drug candidate discovery pipeline run. You can start the full
            AI → Quantum → Docking pipeline from this experiment.
          </p>
        </div>

        <div className="grid lg:grid-cols-5 gap-6">
          {/* Form */}
          <div className="lg:col-span-3 space-y-5 animate-slide-up">

            {error && (
              <div className="p-3 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-sm flex gap-2 items-start">
                <svg className="w-4 h-4 shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                    d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                {error}
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-5">
              {/* Experiment Name */}
              <div>
                <label htmlFor="exp-name" className="block text-xs font-medium text-slate-400 mb-1.5">
                  Experiment Name <span className="text-red-400">*</span>
                </label>
                <input
                  id="exp-name"
                  type="text"
                  required
                  maxLength={300}
                  value={form.name}
                  onChange={e => setForm({ ...form, name: e.target.value })}
                  placeholder="EGFR Bioactivity Screening — Run 1"
                  className="form-input"
                />
                <p className="text-xs text-slate-600 mt-1">{form.name.length}/300 characters</p>
              </div>

              {/* Description */}
              <div>
                <label htmlFor="exp-desc" className="block text-xs font-medium text-slate-400 mb-1.5">
                  Description <span className="text-slate-600">(optional)</span>
                </label>
                <textarea
                  id="exp-desc"
                  rows={3}
                  value={form.description}
                  onChange={e => setForm({ ...form, description: e.target.value })}
                  placeholder="Brief description of this experiment's goal or configuration..."
                  className="form-input resize-none"
                />
              </div>

              {/* Target Selector */}
              <div>
                <label htmlFor="exp-target" className="block text-xs font-medium text-slate-400 mb-1.5">
                  Target
                </label>
                {targetsLoading ? (
                  <div className="form-input flex items-center gap-2 text-slate-500">
                    <div className="w-4 h-4 border-2 border-slate-600 border-t-primary-400 rounded-full animate-spin" />
                    Loading targets...
                  </div>
                ) : (
                  <select
                    id="exp-target"
                    value={form.target_id}
                    onChange={e => setForm({ ...form, target_id: e.target.value })}
                    className="form-input"
                  >
                    <option value="">— No target selected —</option>
                    {targets.map(t => (
                      <option key={t.id} value={t.id}>
                        {t.name}{t.chembl_id ? ` (${t.chembl_id})` : ''}
                      </option>
                    ))}
                  </select>
                )}
              </div>

              {/* Dataset (read-only) */}
              <div>
                <label className="block text-xs font-medium text-slate-400 mb-1.5">Dataset</label>
                <div className="form-input bg-surface-700/30 cursor-default select-none flex items-center gap-2">
                  <svg className="w-4 h-4 text-accent-400 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                      d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                  <span className="text-white text-sm font-mono">{DATASET_INFO.label}</span>
                </div>
                <p className="text-xs text-slate-600 mt-1">
                  Dataset is fixed to the project EGFR dataset. Source: {DATASET_INFO.source}
                </p>
              </div>

              <Button type="submit" loading={submitting} fullWidth className="mt-2">
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                </svg>
                Create Experiment
              </Button>
            </form>
          </div>

          {/* Info sidebar */}
          <div className="lg:col-span-2 space-y-4 animate-slide-up" style={{ animationDelay: '0.1s' }}>

            {/* Target details card */}
            <div className="glass-card p-4">
              <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3">
                Target Details
              </h3>
              {selectedTarget ? (
                <div className="space-y-2">
                  <div>
                    <p className="text-[10px] text-slate-600">Name</p>
                    <p className="text-sm font-medium text-white">{selectedTarget.name}</p>
                  </div>
                  {selectedTarget.chembl_id && (
                    <div>
                      <p className="text-[10px] text-slate-600">ChEMBL ID</p>
                      <p className="text-sm font-mono text-accent-300">{selectedTarget.chembl_id}</p>
                    </div>
                  )}
                  {selectedTarget.uniprot_id && (
                    <div>
                      <p className="text-[10px] text-slate-600">UniProt ID</p>
                      <p className="text-sm font-mono text-primary-300">{selectedTarget.uniprot_id}</p>
                    </div>
                  )}
                  {selectedTarget.organism && (
                    <div>
                      <p className="text-[10px] text-slate-600">Organism</p>
                      <p className="text-sm text-slate-300 italic">{selectedTarget.organism}</p>
                    </div>
                  )}
                  {selectedTarget.target_type && (
                    <div>
                      <p className="text-[10px] text-slate-600">Type</p>
                      <p className="text-sm text-slate-300">{selectedTarget.target_type}</p>
                    </div>
                  )}
                </div>
              ) : (
                <p className="text-sm text-slate-500">Select a target to view details.</p>
              )}
            </div>

            {/* Dataset details card */}
            <div className="glass-card p-4">
              <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3">
                Dataset Details
              </h3>
              <div className="space-y-2">
                <div>
                  <p className="text-[10px] text-slate-600">Name</p>
                  <p className="text-sm font-mono text-white">{DATASET_INFO.label}</p>
                </div>
                <div>
                  <p className="text-[10px] text-slate-600">Source</p>
                  <p className="text-sm text-slate-300">{DATASET_INFO.source}</p>
                </div>
                <div>
                  <p className="text-[10px] text-slate-600">Type</p>
                  <p className="text-sm text-slate-300">{DATASET_INFO.type}</p>
                </div>
                <div>
                  <p className="text-[10px] text-slate-600">Description</p>
                  <p className="text-xs text-slate-500 leading-relaxed">{DATASET_INFO.description}</p>
                </div>
              </div>
            </div>

            {/* Disclaimer */}
            <div className="glass-card p-3 border border-amber-500/15">
              <p className="text-[10px] text-slate-500 leading-relaxed">
                ⚠️ Results are computational predictions only and do not constitute clinical validation or medical advice.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
