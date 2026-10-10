import React, { useState, useEffect, useCallback } from 'react';
import { Link, useParams, useNavigate } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';
import { experimentsApi, pipelineApi } from '../api/client';
import type { ExperimentWithTarget, JobStatus } from '../types';
import { StatusBadge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';

// ── Pipeline visualization data ────────────────────────────────
interface PipelineStageInfo {
  id: string;
  label: string;
  shortLabel: string;
  description: string;
  icon: string;
  statusKey: keyof ExperimentWithTarget | null;
  milestone: string;
}

const PIPELINE_STAGES: PipelineStageInfo[] = [
  {
    id: 'data',
    label: 'Data Collection',
    shortLabel: 'Data',
    description: 'ChEMBL bioactivity IC50 records for EGFR',
    icon: '🔬',
    statusKey: null,
    milestone: 'M1',
  },
  {
    id: 'preprocess',
    label: 'Preprocessing',
    shortLabel: 'Preprocess',
    description: 'Filter, standardize units, calculate pIC50',
    icon: '⚗️',
    statusKey: 'preprocess_status',
    milestone: 'M3',
  },
  {
    id: 'features',
    label: 'Feature Extraction',
    shortLabel: 'Features',
    description: 'RDKit molecular descriptors & Morgan fingerprints',
    icon: '🧬',
    statusKey: 'screen_status',
    milestone: 'M3',
  },
  {
    id: 'ai',
    label: 'AI Prediction',
    shortLabel: 'AI Predict',
    description: 'Random Forest & XGBoost bioactivity prediction',
    icon: '🤖',
    statusKey: 'screen_status',
    milestone: 'M3',
  },
  {
    id: 'filter',
    label: 'Candidate Filtering',
    shortLabel: 'Filter',
    description: "Lipinski Rule of Five & drug-likeness screening",
    icon: '🔍',
    statusKey: 'screen_status',
    milestone: 'M3',
  },
  {
    id: 'quantum',
    label: 'Quantum Optimization',
    shortLabel: 'Quantum',
    description: 'QAOA via Qiskit vs. classical solver',
    icon: '⚛️',
    statusKey: 'quantum_status',
    milestone: 'M4',
  },
  {
    id: 'docking',
    label: 'Molecular Docking',
    shortLabel: 'Docking',
    description: 'AutoDock Vina binding affinity',
    icon: '🏗️',
    statusKey: 'docking_status',
    milestone: 'M5',
  },
  {
    id: 'validate',
    label: 'Validation',
    shortLabel: 'Validate',
    description: 'Methodology check & confidence scoring',
    icon: '✅',
    statusKey: null,
    milestone: 'M6',
  },
  {
    id: 'rank',
    label: 'Final Ranking',
    shortLabel: 'Rank',
    description: 'Composite scoring & report generation',
    icon: '🏆',
    statusKey: null,
    milestone: 'M6',
  },
];

const getStageStatus = (stage: PipelineStageInfo, experiment: ExperimentWithTarget): JobStatus | 'not_started' => {
  if (stage.id === 'data') {
    return experiment.dataset_path ? 'COMPLETED' : 'PENDING';
  }
  if (!stage.statusKey) return 'PENDING';
  const raw = experiment[stage.statusKey];
  if (raw && typeof raw === 'string') return raw as JobStatus;
  return 'PENDING';
};

const stageStatusLabel: Record<string, string> = {
  COMPLETED: 'Completed',
  RUNNING:   'Running',
  PENDING:   'Not Started',
  FAILED:    'Failed',
  not_started: 'Not Started',
};

const stageStatusColor: Record<string, string> = {
  COMPLETED:   'text-success-400 border-success-500/30 bg-success-500/10',
  RUNNING:     'text-warning-400 border-warning-500/30 bg-warning-500/10',
  PENDING:     'text-slate-500 border-white/5 bg-surface-700/30',
  FAILED:      'text-red-400 border-red-500/30 bg-red-500/10',
  not_started: 'text-slate-500 border-white/5 bg-surface-700/30',
};

const formatDate = (iso: string) =>
  new Date(iso).toLocaleDateString('en-GB', {
    day: '2-digit', month: 'short', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  });

const getDatasetLabel = (path: string | null) => {
  if (!path) return '—';
  return path.split('/').pop() ?? path;
};

const Skeleton: React.FC = () => (
  <div className="animate-pulse space-y-4">
    <div className="h-8 bg-surface-600 rounded w-1/2" />
    <div className="h-4 bg-surface-700 rounded w-1/4" />
    <div className="grid grid-cols-4 gap-4 mt-6">
      {[1, 2, 3, 4].map(i => <div key={i} className="h-20 bg-surface-700 rounded-xl" />)}
    </div>
    <div className="h-64 bg-surface-700 rounded-xl mt-4" />
  </div>
);

export const ExperimentDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { isAuthenticated } = useAuthStore();

  const [experiment, setExperiment] = useState<ExperimentWithTarget | null>(null);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!isAuthenticated) navigate('/login');
  }, [isAuthenticated, navigate]);

  const loadExperiment = useCallback(async () => {
    if (!id) return;
    setLoading(true);
    setError(null);
    try {
      const res = await experimentsApi.get(parseInt(id, 10));
      setExperiment(res.data);
    } catch (err: unknown) {
      const axiosErr = err as { response?: { status?: number } };
      if (axiosErr?.response?.status === 404) {
        setError('Experiment not found.');
      } else {
        setError('Failed to load experiment. Is the backend running?');
      }
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    loadExperiment();
  }, [loadExperiment]);

  const handlePreprocess = async () => {
    if (!id) return;
    setActionLoading(true);
    try {
      await pipelineApi.preprocess(parseInt(id, 10));
      await loadExperiment();
    } catch {
      alert('Preprocessing failed.');
    } finally {
      setActionLoading(false);
    }
  };

  const handlePredict = async () => {
    if (!id) return;
    setActionLoading(true);
    try {
      await pipelineApi.predict(parseInt(id, 10));
      await loadExperiment();
      navigate(`/experiments/${id}/ai`);
    } catch {
      alert('Prediction failed.');
    } finally {
      setActionLoading(false);
    }
  };

  if (!isAuthenticated) return null;

  return (
    <div className="min-h-screen pt-16 pl-56">
      <div className="p-8 max-w-5xl">

        {/* Breadcrumb */}
        <div className="flex items-center gap-2 text-sm text-slate-500 mb-6 animate-slide-up">
          <Link to="/experiments" className="hover:text-slate-300 transition-colors">Experiments</Link>
          <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
          </svg>
          <span className="text-slate-400 truncate max-w-xs">
            {experiment?.name ?? `Experiment #${id}`}
          </span>
        </div>

        {/* Loading */}
        {loading && <Skeleton />}

        {/* Error */}
        {!loading && error && (
          <div className="glass-card p-8 text-center border border-red-500/20">
            <svg className="w-10 h-10 text-red-400 mx-auto mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <h2 className="text-white font-semibold mb-2">{error}</h2>
            <Link to="/experiments">
              <Button variant="secondary" size="sm">← Back to Experiments</Button>
            </Link>
          </div>
        )}

        {/* Experiment content */}
        {!loading && experiment && (
          <div className="space-y-6 animate-fade-in">

            {/* Header */}
            <div className="flex items-start justify-between gap-4">
              <div className="min-w-0">
                <div className="section-divider mb-3" />
                <h1 className="text-2xl font-bold text-white mb-1 truncate">{experiment.name}</h1>
                {experiment.description && (
                  <p className="text-slate-400 text-sm">{experiment.description}</p>
                )}
              </div>
              <div className="shrink-0 flex items-center gap-3">
                <StatusBadge status={experiment.status} />
                <Link to="/experiments">
                  <Button variant="ghost" size="sm">← Back</Button>
                </Link>
              </div>
            </div>

            {/* Action Bar for Pipeline */}
            <div className="glass-card p-4 flex flex-wrap items-center justify-between gap-4 border-l-4 border-l-primary-500">
              <div>
                <h3 className="text-sm font-bold text-white">Pipeline Execution Controls</h3>
                <p className="text-xs text-slate-400">Run preprocessing, ML screening, ADMET filtering, and QAOA optimization.</p>
              </div>
              <div className="flex flex-wrap items-center gap-3">
                <Button
                  size="sm"
                  variant="secondary"
                  onClick={handlePreprocess}
                  loading={actionLoading}
                >
                  ⚗️ Preprocess
                </Button>
                <Button
                  size="sm"
                  onClick={handlePredict}
                  loading={actionLoading}
                >
                  🤖 AI Screen
                </Button>
                <Link to={`/experiments/${id}/ai`}>
                  <Button size="sm" variant="ghost" className="border border-primary-500/30 text-primary-300">
                    📊 AI Results
                  </Button>
                </Link>
                <Link to={`/experiments/${id}/admet`}>
                  <Button size="sm" variant="ghost" className="border border-success-500/30 text-success-300">
                    🧪 ADMET
                  </Button>
                </Link>
                <Link to={`/experiments/${id}/quantum`}>
                  <Button size="sm" variant="ghost" className="border border-accent-500/30 text-accent-300">
                    ⚛️ QAOA
                  </Button>
                </Link>
                <Link to={`/experiments/${id}/docking`}>
                  <Button size="sm" variant="ghost" className="border border-teal-500/30 text-teal-300">
                    🔬 Docking
                  </Button>
                </Link>
                <Link to={`/experiments/${id}/ranking`}>
                  <Button size="sm" variant="ghost" className="border border-yellow-500/30 text-yellow-300">
                    🏆 Rankings
                  </Button>
                </Link>
              </div>
            </div>

            {/* Meta grid */}
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
              {/* Target */}
              <div className="glass-card p-4">
                <p className="text-xs text-slate-500 mb-1">Target</p>
                {experiment.target ? (
                  <div>
                    <p className="text-sm font-semibold text-white">{experiment.target.chembl_id ?? '—'}</p>
                    <p className="text-xs text-slate-400 truncate">{experiment.target.name}</p>
                  </div>
                ) : (
                  <p className="text-sm text-slate-500">—</p>
                )}
              </div>

              {/* Dataset */}
              <div className="glass-card p-4">
                <p className="text-xs text-slate-500 mb-1">Dataset</p>
                <p className="text-sm font-mono text-white truncate">
                  {getDatasetLabel(experiment.dataset_path)}
                </p>
                <p className="text-xs text-slate-500">
                  {experiment.processed_record_count
                    ? `${experiment.processed_record_count.toLocaleString()} molecules`
                    : experiment.raw_record_count
                    ? `${experiment.raw_record_count.toLocaleString()} raw records`
                    : '18,454 records available'}
                </p>
              </div>

              {/* Created */}
              <div className="glass-card p-4">
                <p className="text-xs text-slate-500 mb-1">Created</p>
                <p className="text-sm text-white">{formatDate(experiment.created_at)}</p>
              </div>

              {/* Updated */}
              <div className="glass-card p-4">
                <p className="text-xs text-slate-500 mb-1">Last Updated</p>
                <p className="text-sm text-white">
                  {experiment.updated_at ? formatDate(experiment.updated_at) : '—'}
                </p>
              </div>
            </div>

            {/* Target details */}
            {experiment.target && (
              <div className="glass-card p-5">
                <h2 className="text-sm font-semibold text-white mb-4 flex items-center gap-2">
                  <span className="text-base">🎯</span>
                  Target: {experiment.target.name}
                </h2>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  {[
                    { label: 'ChEMBL ID', value: experiment.target.chembl_id, mono: true, color: 'text-accent-300' },
                    { label: 'UniProt ID', value: experiment.target.uniprot_id, mono: true, color: 'text-primary-300' },
                    { label: 'Organism', value: experiment.target.organism, mono: false, color: 'text-white' },
                    { label: 'Type', value: experiment.target.target_type, mono: false, color: 'text-white' },
                  ].map(field => (
                    <div key={field.label}>
                      <p className="text-[10px] text-slate-600 mb-0.5">{field.label}</p>
                      <p className={`text-sm ${field.mono ? 'font-mono' : ''} ${field.color}`}>
                        {field.value ?? '—'}
                      </p>
                    </div>
                  ))}
                </div>
                {experiment.target.description && (
                  <p className="text-xs text-slate-500 leading-relaxed mt-4 border-t border-white/5 pt-4">
                    {experiment.target.description}
                  </p>
                )}
              </div>
            )}

            {/* Pipeline visualization */}
            <div className="glass-card p-5">
              <h2 className="text-sm font-semibold text-white mb-1">Discovery Pipeline</h2>
              <p className="text-xs text-slate-500 mb-5">
                Showing live pipeline stage status. Preprocessing and AI Prediction (M3) are active.
              </p>

              <div className="space-y-2">
                {PIPELINE_STAGES.map((stage, idx) => {
                  const stageStatus = getStageStatus(stage, experiment);
                  const statusLabel = stageStatusLabel[stageStatus] ?? stageStatus;
                  const statusCls = stageStatusColor[stageStatus] ?? stageStatusColor.PENDING;

                  return (
                    <div key={stage.id} className="flex items-center gap-4">
                      {/* Step number + connector */}
                      <div className="flex flex-col items-center shrink-0" style={{ width: '32px' }}>
                        <div className={`w-8 h-8 rounded-xl flex items-center justify-center text-sm border ${statusCls}`}>
                          {stage.icon}
                        </div>
                        {idx < PIPELINE_STAGES.length - 1 && (
                          <div className="w-px h-4 bg-white/5 mt-1" />
                        )}
                      </div>

                      {/* Stage info */}
                      <div className="flex-1 min-w-0 py-1">
                        <div className="flex items-center gap-2">
                          <span className="text-sm font-medium text-white">{stage.label}</span>
                          <span className="text-[10px] text-slate-600 bg-surface-700 px-1.5 py-0.5 rounded">
                            {stage.milestone}
                          </span>
                        </div>
                        <p className="text-xs text-slate-500">{stage.description}</p>
                      </div>

                      {/* Status pill */}
                      <div className={`text-xs px-2.5 py-1 rounded-lg border shrink-0 font-medium ${statusCls}`}>
                        {statusLabel}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Scientific disclaimer */}
            <div className="glass-card p-4 border border-amber-500/15 text-center">
              <p className="text-xs text-slate-500">
                ⚠️ Results from this pipeline are computational predictions only.
                They do not constitute clinical validation or medical advice.
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
