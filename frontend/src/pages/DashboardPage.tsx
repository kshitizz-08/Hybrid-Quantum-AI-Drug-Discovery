import React, { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';
import { healthApi, experimentsApi } from '../api/client';
import type { DashboardStats, ExperimentListItem } from '../types';
import { StatusBadge } from '../components/ui/Badge';
import { StatCard } from '../components/ui/Card';
import { Button } from '../components/ui/Button';

// ── Format helpers ─────────────────────────────────────────────
const formatDate = (iso: string) =>
  new Date(iso).toLocaleDateString('en-GB', {
    day: '2-digit', month: 'short', year: 'numeric',
  });

const getDatasetLabel = (path: string | null) =>
  path ? (path.split('/').pop() ?? path) : '—';

// ── Stat skeleton ──────────────────────────────────────────────
const StatSkeleton: React.FC = () => (
  <div className="glass-card p-5 animate-pulse">
    <div className="h-3 bg-surface-600 rounded w-1/2 mb-3" />
    <div className="h-7 bg-surface-500 rounded w-1/3" />
  </div>
);

export const DashboardPage: React.FC = () => {
  const { user, isAuthenticated } = useAuthStore();
  const navigate = useNavigate();

  const [health, setHealth] = useState<{ connected: boolean; url_type: string; version: string } | null>(null);
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [recentExperiments, setRecentExperiments] = useState<ExperimentListItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!isAuthenticated) navigate('/login');
  }, [isAuthenticated, navigate]);

  useEffect(() => {
    if (!isAuthenticated) return;

    const loadAll = async () => {
      setLoading(true);

      // Health check
      try {
        const res = await healthApi.check();
        setHealth({
          connected: res.data.database.connected,
          url_type: res.data.database.url_type,
          version: res.data.version,
        });
      } catch {
        setHealth(null);
      }

      // Dashboard stats
      try {
        const statsRes = await experimentsApi.stats();
        setStats(statsRes.data);
      } catch {
        setStats(null);
      }

      // Recent experiments (first 5)
      try {
        const expRes = await experimentsApi.list();
        setRecentExperiments((expRes.data as ExperimentListItem[]).slice(0, 5));
      } catch {
        setRecentExperiments([]);
      }

      setLoading(false);
    };

    loadAll();
  }, [isAuthenticated]);

  if (!isAuthenticated) return null;

  return (
    <div className="min-h-screen pt-16 pl-56">
      <div className="p-8 max-w-6xl">

        {/* Header */}
        <div className="mb-8 animate-slide-up">
          <p className="text-slate-500 text-sm mb-1">Welcome back,</p>
          <h1 className="text-3xl font-bold text-white">
            {user?.full_name || user?.username}
          </h1>
          <p className="text-slate-400 mt-1">
            Hybrid Quantum-AI Drug Discovery Platform
          </p>
        </div>

        {/* Backend health banner */}
        <div className={`mb-6 inline-flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm border animate-fade-in ${
          health?.connected
            ? 'bg-success-500/10 border-success-500/20 text-success-400'
            : 'bg-red-500/10 border-red-500/20 text-red-400'
        }`}>
          <span className={`w-2 h-2 rounded-full ${health?.connected ? 'bg-success-400 animate-pulse' : 'bg-red-400'}`} />
          {health === null
            ? 'Backend unreachable — start the FastAPI server on port 8000'
            : `Backend connected · DB: ${health.url_type} · v${health.version}`
          }
        </div>

        {/* Stats row */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8 stagger-children">
          {loading ? (
            [1, 2, 3, 4].map(i => <StatSkeleton key={i} />)
          ) : (
            <>
              <StatCard
                label="Total Experiments"
                value={stats?.total_experiments ?? 0}
                color="primary"
                icon={
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                      d="M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z" />
                  </svg>
                }
              />
              <StatCard
                label="Active Experiments"
                value={stats?.active_experiments ?? 0}
                color="warning"
                icon={
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                      d="M13 10V3L4 14h7v7l9-11h-7z" />
                  </svg>
                }
              />
              <StatCard
                label="Completed"
                value={stats?.completed_experiments ?? 0}
                color="success"
                icon={
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                      d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                }
              />
              <StatCard
                label="Targets Available"
                value={stats?.total_targets ?? 0}
                color="accent"
                icon={
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                      d="M14.121 14.121L19 19m-7-7l7-7m-7 7l-2.879 2.879M12 12L9.121 9.121m0 5.758a3 3 0 10-4.243 4.243 3 3 0 004.243-4.243zm0-5.758a3 3 0 10-4.243-4.243 3 3 0 004.243 4.243z" />
                  </svg>
                }
              />
            </>
          )}
        </div>

        {/* Recent experiments or empty state */}
        {!loading && recentExperiments.length === 0 ? (
          <div className="glass-card p-12 text-center animate-fade-in">
            <div className="w-16 h-16 rounded-2xl bg-primary-500/10 flex items-center justify-center mx-auto mb-4">
              <svg className="w-8 h-8 text-primary-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                  d="M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z" />
              </svg>
            </div>
            <h2 className="text-xl font-semibold text-white mb-2">No experiments yet</h2>
            <p className="text-slate-400 mb-6 max-w-md mx-auto text-sm">
              Start your first drug discovery experiment. Load the EGFR dataset,
              run the AI pipeline, and explore computationally predicted candidates.
            </p>
            <Link to="/new-discovery">
              <Button>
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                </svg>
                Start New Discovery
              </Button>
            </Link>
          </div>
        ) : !loading ? (
          <div className="animate-fade-in">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-base font-semibold text-white">Recent Experiments</h2>
              <Link to="/experiments" className="text-xs text-primary-400 hover:text-primary-300 transition-colors">
                View all →
              </Link>
            </div>
            <div className="space-y-2">
              {recentExperiments.map(exp => (
                <Link
                  key={exp.id}
                  to={`/experiments/${exp.id}`}
                  className="glass-card-hover p-4 flex items-center gap-4"
                >
                  {/* Icon */}
                  <div className="w-9 h-9 rounded-lg bg-primary-500/10 flex items-center justify-center shrink-0">
                    <svg className="w-4 h-4 text-primary-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                        d="M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z" />
                    </svg>
                  </div>

                  {/* Name + target */}
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-white truncate">{exp.name}</p>
                    <p className="text-xs text-slate-500 truncate">
                      {exp.target?.chembl_id ?? '—'} · {getDatasetLabel(exp.dataset_path)}
                    </p>
                  </div>

                  {/* Status + Date */}
                  <div className="flex items-center gap-3 shrink-0">
                    <StatusBadge status={exp.status} />
                    <span className="text-xs text-slate-600 hidden sm:inline">{formatDate(exp.created_at)}</span>
                  </div>
                </Link>
              ))}
            </div>
          </div>
        ) : null}

        {/* Pipeline overview strip */}
        {!loading && (
          <div className="mt-8 animate-fade-in">
            <h2 className="text-sm font-semibold text-white mb-4">Discovery Pipeline</h2>
            <div className="glass-card p-4">
              <div className="flex items-center justify-between gap-1 overflow-x-auto pb-1">
                {['Data', 'Preprocess', 'Features', 'AI Predict', 'Filter', 'Quantum', 'Docking', 'Validate', 'Rank'].map((step, i) => (
                  <React.Fragment key={step}>
                    <div className="flex flex-col items-center gap-1 shrink-0">
                      <div className="w-8 h-8 rounded-lg bg-surface-700 border border-white/5 flex items-center justify-center text-xs text-slate-500 font-bold">
                        {i + 1}
                      </div>
                      <span className="text-[9px] text-slate-600 text-center whitespace-nowrap">{step}</span>
                    </div>
                    {i < 8 && <div className="w-4 h-px bg-white/5 shrink-0 mt-[-12px]" />}
                  </React.Fragment>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
