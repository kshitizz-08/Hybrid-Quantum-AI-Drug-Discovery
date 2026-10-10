import React, { useState, useEffect, useCallback } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';
import { experimentsApi } from '../api/client';
import type { ExperimentListItem } from '../types';
import { StatusBadge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';

// ── Format helpers ─────────────────────────────────────────────
const formatDate = (iso: string) =>
  new Date(iso).toLocaleDateString('en-GB', {
    day: '2-digit', month: 'short', year: 'numeric',
  });

const getDatasetLabel = (path: string | null) => {
  if (!path) return '—';
  return path.split('/').pop() ?? path;
};

// ── Loading skeleton ───────────────────────────────────────────
const SkeletonRow: React.FC = () => (
  <div className="glass-card p-4 animate-pulse flex items-center gap-4">
    <div className="w-8 h-8 rounded-lg bg-surface-600 shrink-0" />
    <div className="flex-1 space-y-2">
      <div className="h-4 bg-surface-600 rounded w-1/3" />
      <div className="h-3 bg-surface-700 rounded w-1/5" />
    </div>
    <div className="h-6 bg-surface-600 rounded-full w-20" />
    <div className="h-8 bg-surface-600 rounded-lg w-16" />
  </div>
);

export const ExperimentsPage: React.FC = () => {
  const navigate = useNavigate();
  const { isAuthenticated } = useAuthStore();

  const [experiments, setExperiments] = useState<ExperimentListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [deleting, setDeleting] = useState<number | null>(null);

  useEffect(() => {
    if (!isAuthenticated) navigate('/login');
  }, [isAuthenticated, navigate]);

  const fetchExperiments = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await experimentsApi.list();
      setExperiments(res.data);
    } catch {
      setError('Failed to load experiments. Is the backend running?');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchExperiments();
  }, [fetchExperiments]);

  const handleDelete = async (id: number, name: string) => {
    if (!window.confirm(`Delete "${name}"? This cannot be undone.`)) return;
    setDeleting(id);
    try {
      await experimentsApi.delete(id);
      setExperiments(prev => prev.filter(e => e.id !== id));
    } catch {
      alert('Failed to delete experiment.');
    } finally {
      setDeleting(null);
    }
  };

  if (!isAuthenticated) return null;

  return (
    <div className="min-h-screen pt-16 pl-56">
      <div className="p-8 max-w-6xl">

        {/* Header */}
        <div className="flex items-center justify-between mb-8 animate-slide-up">
          <div>
            <div className="section-divider mb-3" />
            <h1 className="text-2xl font-bold text-white">Experiments</h1>
            <p className="text-slate-400 text-sm mt-1">
              All your drug discovery pipeline runs
            </p>
          </div>
          <Link to="/new-discovery">
            <Button size="sm">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
              </svg>
              New Experiment
            </Button>
          </Link>
        </div>

        {/* Error state */}
        {error && (
          <div className="glass-card p-4 border border-red-500/20 mb-6 flex items-center gap-3 text-red-400 animate-fade-in">
            <svg className="w-5 h-5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <span className="text-sm">{error}</span>
            <button onClick={fetchExperiments} className="ml-auto text-xs underline hover:no-underline">
              Retry
            </button>
          </div>
        )}

        {/* Loading */}
        {loading && (
          <div className="space-y-3">
            {[1, 2, 3].map(i => <SkeletonRow key={i} />)}
          </div>
        )}

        {/* Empty state */}
        {!loading && !error && experiments.length === 0 && (
          <div className="glass-card p-12 text-center animate-fade-in">
            <div className="w-14 h-14 rounded-2xl bg-primary-500/10 flex items-center justify-center mx-auto mb-4">
              <svg className="w-7 h-7 text-primary-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                  d="M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z" />
              </svg>
            </div>
            <h2 className="text-lg font-semibold text-white mb-2">No experiments yet</h2>
            <p className="text-slate-400 text-sm mb-6 max-w-md mx-auto">
              Create your first drug discovery experiment. Load the EGFR dataset,
              run the AI pipeline, and explore computationally predicted candidates.
            </p>
            <Link to="/new-discovery">
              <Button>
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                </svg>
                Create First Experiment
              </Button>
            </Link>
          </div>
        )}

        {/* Experiments list */}
        {!loading && !error && experiments.length > 0 && (
          <div className="space-y-3 animate-fade-in">
            {/* Column headers */}
            <div className="hidden lg:grid grid-cols-[2fr_1fr_1fr_1fr_1fr_100px] gap-4 px-4 text-xs text-slate-600 font-medium uppercase tracking-wider">
              <span>Experiment</span>
              <span>Target</span>
              <span>Dataset</span>
              <span>Status</span>
              <span>Created</span>
              <span></span>
            </div>

            {experiments.map(exp => (
              <div
                key={exp.id}
                className="glass-card-hover p-4 grid lg:grid-cols-[2fr_1fr_1fr_1fr_1fr_100px] gap-4 items-center"
              >
                {/* Name + Description */}
                <div className="min-w-0">
                  <Link
                    to={`/experiments/${exp.id}`}
                    className="text-sm font-semibold text-white hover:text-primary-300 transition-colors truncate block"
                  >
                    {exp.name}
                  </Link>
                  {exp.description && (
                    <p className="text-xs text-slate-500 truncate mt-0.5">{exp.description}</p>
                  )}
                  {/* Mobile-only metadata */}
                  <div className="flex items-center gap-2 mt-1 lg:hidden">
                    <StatusBadge status={exp.status} />
                    <span className="text-xs text-slate-600">{formatDate(exp.created_at)}</span>
                  </div>
                </div>

                {/* Target */}
                <div className="hidden lg:block">
                  {exp.target ? (
                    <div>
                      <p className="text-sm text-white">{exp.target.chembl_id ?? exp.target.name}</p>
                      <p className="text-xs text-slate-500">{exp.target.organism ?? ''}</p>
                    </div>
                  ) : (
                    <span className="text-sm text-slate-600">—</span>
                  )}
                </div>

                {/* Dataset */}
                <div className="hidden lg:block">
                  <p className="text-xs font-mono text-slate-400 truncate">
                    {getDatasetLabel(exp.dataset_path)}
                  </p>
                  {exp.raw_record_count && (
                    <p className="text-xs text-slate-600">
                      {exp.raw_record_count.toLocaleString()} records
                    </p>
                  )}
                </div>

                {/* Status */}
                <div className="hidden lg:block">
                  <StatusBadge status={exp.status} />
                </div>

                {/* Created date */}
                <div className="hidden lg:block">
                  <p className="text-xs text-slate-400">{formatDate(exp.created_at)}</p>
                </div>

                {/* Actions */}
                <div className="flex items-center gap-2">
                  <Link to={`/experiments/${exp.id}`}>
                    <Button size="sm" variant="secondary">Open</Button>
                  </Link>
                  <button
                    onClick={() => handleDelete(exp.id, exp.name)}
                    disabled={deleting === exp.id}
                    className="p-1.5 rounded-lg text-slate-600 hover:text-red-400 hover:bg-red-500/10 transition-colors"
                    title="Delete experiment"
                  >
                    {deleting === exp.id ? (
                      <div className="w-4 h-4 border-2 border-red-400/30 border-t-red-400 rounded-full animate-spin" />
                    ) : (
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                          d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                      </svg>
                    )}
                  </button>
                </div>
              </div>
            ))}

            <p className="text-xs text-slate-600 pt-1 px-1">
              Showing {experiments.length} experiment{experiments.length !== 1 ? 's' : ''}
            </p>
          </div>
        )}
      </div>
    </div>
  );
};
