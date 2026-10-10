import React, { useState, useEffect, useCallback } from 'react';
import { Link, useParams, useNavigate } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';
import { experimentsApi, admetApi } from '../api/client';

interface ADMETMolecule {
  molecule_chembl_id: string;
  smiles: string;
  predicted_pIC50: number;
  pIC50: number;
  tox_probability: number | null;
  tox_label: string;
  predicted_log_solubility: number | null;
  solubility_label: string;
  composite_score: number;
  bioactivity_norm: number;
  toxicity_risk_norm: number;
  solubility_norm: number;
  drug_likeness_norm: number;
  lipinski_pass: boolean;
  molecular_weight: number;
  logP: number;
  TPSA: number;
  HBD: number;
  HBA: number;
}

interface ADMETData {
  total_filtered: number;
  returned: number;
  filter_config: Record<string, unknown>;
  score_formula: { description: string; reference: string };
  molecules: ADMETMolecule[];
  disclaimer: string;
}

const toxBadge = (label: string) => {
  if (label === 'Safe') return 'bg-success-500/15 text-success-400 border-success-500/30';
  if (label === 'Toxic Risk') return 'bg-red-500/15 text-red-400 border-red-500/30';
  return 'bg-slate-500/10 text-slate-500 border-white/5';
};

const solBadge = (label: string) => {
  if (label === 'Good') return 'bg-success-500/15 text-success-400';
  if (label === 'Moderate') return 'bg-amber-500/15 text-amber-400';
  if (label === 'Poor') return 'bg-red-500/15 text-red-400';
  return 'text-slate-500';
};

const ScoreBar: React.FC<{ value: number; color?: string }> = ({ value, color = 'bg-primary-500' }) => (
  <div className="flex items-center gap-2 w-full">
    <div className="flex-1 h-1.5 bg-surface-700 rounded-full overflow-hidden">
      <div className={`h-full ${color} rounded-full`} style={{ width: `${Math.round(value * 100)}%` }} />
    </div>
    <span className="text-[11px] font-mono text-slate-400 w-8">{(value * 100).toFixed(0)}%</span>
  </div>
);

export const ADMETPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { isAuthenticated } = useAuthStore();

  const [admetData, setAdmetData] = useState<ADMETData | null>(null);
  const [modelInfo, setModelInfo] = useState<Record<string, unknown> | null>(null);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expName, setExpName] = useState('');

  // Filter state
  const [minPic50, setMinPic50] = useState(5.0);
  const [maxTox, setMaxTox] = useState(1.0);
  const [minLogSol, setMinLogSol] = useState(-10.0);
  const [requireLipinski, setRequireLipinski] = useState(false);
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);
  const pageSize = 25;

  useEffect(() => {
    if (!isAuthenticated) navigate('/login');
  }, [isAuthenticated, navigate]);

  const fetchData = useCallback(async () => {
    if (!id) return;
    const expId = parseInt(id, 10);
    setLoading(true);
    setError(null);
    try {
      const expRes = await experimentsApi.get(expId);
      setExpName(expRes.data.name ?? `Experiment #${id}`);

      const modelRes = await admetApi.getModelInfo(expId);
      setModelInfo(modelRes.data);

      const admetRes = await admetApi.getResults(expId, {
        min_pic50: minPic50,
        max_tox_risk: maxTox,
        min_log_sol: minLogSol,
        require_lipinski: requireLipinski,
        limit: pageSize,
        offset: (page - 1) * pageSize,
        search: search.trim() || undefined,
      });
      setAdmetData(admetRes.data);
    } catch {
      // Results may not exist yet — don't show error, just leave empty
    } finally {
      setLoading(false);
    }
  }, [id, minPic50, maxTox, minLogSol, requireLipinski, search, page]);

  useEffect(() => { fetchData(); }, [fetchData]);

  const handleRunScreening = async () => {
    if (!id) return;
    setRunning(true);
    setError(null);
    try {
      await admetApi.runScreening(parseInt(id, 10), 100);
      await fetchData();
    } catch (e: unknown) {
      const detail = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setError(detail || 'ADMET screening failed. Please try again.');
    } finally {
      setRunning(false);
    }
  };

  const toxMeta = modelInfo?.toxicity_model as Record<string, unknown> | null;
  const solMeta = modelInfo?.solubility_model as Record<string, unknown> | null;

  if (!isAuthenticated) return null;

  return (
    <div className="min-h-screen pt-16 pl-56">
      <div className="p-8 max-w-7xl space-y-6">

        {/* Breadcrumb */}
        <div className="flex items-center gap-2 text-sm text-slate-500 animate-slide-up">
          <Link to="/experiments" className="hover:text-slate-300 transition-colors">Experiments</Link>
          <span>/</span>
          <Link to={`/experiments/${id}`} className="hover:text-slate-300 transition-colors">{expName}</Link>
          <span>/</span>
          <span className="text-white font-medium">ADMET Screening</span>
        </div>

        {/* Header */}
        <div className="flex items-start justify-between gap-4">
          <div>
            <div className="section-divider mb-3" />
            <h1 className="text-2xl font-bold text-white">ADMET Screening</h1>
            <p className="text-slate-400 text-sm mt-1">
              Toxicity (Tox21 NR-AR) · Solubility (Delaney ESOL) · Composite Drug-likeness Scoring
            </p>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={handleRunScreening}
              disabled={running}
              className="px-4 py-2 rounded-xl text-sm font-semibold bg-primary-500 hover:bg-primary-600 text-white transition-all disabled:opacity-50"
            >
              {running ? '⏳ Running...' : '🧪 Run ADMET Screening'}
            </button>
            <Link to={`/experiments/${id}/quantum`}>
              <button className="px-4 py-2 rounded-xl text-sm font-semibold bg-accent-500/20 border border-accent-500/40 text-accent-300 hover:bg-accent-500/30 transition-all">
                ⚛️ Quantum Optimization →
              </button>
            </Link>
            <Link to={`/experiments/${id}`}>
              <button className="px-3 py-2 rounded-xl text-sm text-slate-400 hover:text-white transition-colors">← Back</button>
            </Link>
          </div>
        </div>

        {/* Error / Fallback banners */}
        {error && (
          <div className="bg-rose-500/10 border border-rose-500/30 rounded-xl px-4 py-3 text-rose-300 text-sm flex items-start gap-2">
            <span>⚠️</span>
            <span>{error}</span>
            <button onClick={() => setError(null)} className="ml-auto text-rose-400 hover:text-rose-300">✕</button>
          </div>
        )}

        {/* Model Cards */}
        <div className="grid md:grid-cols-2 gap-4">
          {/* Toxicity Model */}
          <div className="glass-card p-5 space-y-3">
            <div className="flex items-center justify-between pb-2 border-b border-white/5">
              <h2 className="text-sm font-semibold text-white flex items-center gap-2">☣️ Toxicity Model</h2>
              <span className="text-[10px] font-mono text-slate-500 bg-surface-700 px-2 py-0.5 rounded">Tox21 NR-AR</span>
            </div>
            {toxMeta ? (
              <div className="text-xs space-y-1.5">
                {[
                  ['Dataset', 'Tox21 — MoleculeNet'],
                  ['Endpoint', 'NR-AR (Androgen Receptor)'],
                  ['Label Type', 'Binary (0=Safe, 1=Toxic)'],
                  ['Accuracy', `${((toxMeta.metrics as Record<string,number>)?.accuracy * 100).toFixed(1)}%`],
                  ['ROC-AUC', `${((toxMeta.metrics as Record<string,number>)?.ROC_AUC).toFixed(4)} (primary metric)`],
                  ['F1 Score', `${((toxMeta.metrics as Record<string,number>)?.F1).toFixed(4)}`],
                ].map(([k, v]) => (
                  <div key={k} className="flex justify-between border-b border-white/5 py-1">
                    <span className="text-slate-500">{k}</span>
                    <span className="text-slate-300 font-mono">{v}</span>
                  </div>
                ))}
                <p className="text-[10px] text-amber-400 pt-1">⚠️ Class imbalanced: 309 toxic vs 6,956 non-toxic. ROC-AUC is primary metric.</p>
              </div>
            ) : <p className="text-xs text-slate-500">Model metadata unavailable. Run training first.</p>}
          </div>

          {/* Solubility Model */}
          <div className="glass-card p-5 space-y-3">
            <div className="flex items-center justify-between pb-2 border-b border-white/5">
              <h2 className="text-sm font-semibold text-white flex items-center gap-2">💧 Solubility Model</h2>
              <span className="text-[10px] font-mono text-slate-500 bg-surface-700 px-2 py-0.5 rounded">Delaney ESOL</span>
            </div>
            {solMeta ? (
              <div className="text-xs space-y-1.5">
                {[
                  ['Dataset', 'Delaney ESOL (2004)'],
                  ['Target', 'log10(mol/L) solubility'],
                  ['Model', 'Random Forest Regressor'],
                  ['MAE', `${((solMeta.metrics as Record<string,number>)?.MAE).toFixed(4)}`],
                  ['RMSE', `${((solMeta.metrics as Record<string,number>)?.RMSE).toFixed(4)}`],
                  ['R²', `${((solMeta.metrics as Record<string,number>)?.R2).toFixed(4)}`],
                ].map(([k, v]) => (
                  <div key={k} className="flex justify-between border-b border-white/5 py-1">
                    <span className="text-slate-500">{k}</span>
                    <span className="text-slate-300 font-mono">{v}</span>
                  </div>
                ))}
                <p className="text-[10px] text-slate-500 pt-1">Citation: Delaney (2004) J. Chem. Inf. Comput. Sci., 44(3), 1000-1005.</p>
              </div>
            ) : <p className="text-xs text-slate-500">Model metadata unavailable.</p>}
          </div>
        </div>

        {/* Scoring Formula */}
        <div className="glass-card p-4 border-l-4 border-l-accent-500 text-xs">
          <p className="font-semibold text-white mb-1">Composite Scoring Formula</p>
          <code className="text-accent-300 bg-surface-800 px-3 py-1.5 rounded block font-mono text-[11px]">
            composite = 0.40 × bioactivity_norm − 0.30 × toxicity_risk_norm + 0.20 × solubility_norm + 0.10 × drug_likeness_norm
          </code>
          <p className="text-slate-500 mt-1.5">All components normalized to [0,1]. Source: <code>ml/admet/scoring.py</code></p>
        </div>

        {/* Candidate Table */}
        <div className="glass-card p-6 space-y-4">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-white/10 pb-4">
            <div>
              <h2 className="text-lg font-bold text-white">🔬 ADMET Candidate Molecules</h2>
              <p className="text-xs text-slate-400">
                {admetData ? `${admetData.total_filtered.toLocaleString()} candidates matching filters` : 'Run screening to populate'}
              </p>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <input type="text" placeholder="Search ChEMBL ID..." value={search}
                onChange={e => { setSearch(e.target.value); setPage(1); }}
                className="bg-surface-700 border border-white/10 rounded-xl px-3 py-1.5 text-xs text-white placeholder-slate-500 w-44 outline-none focus:border-primary-500" />
              <input type="number" placeholder="Min pIC50" value={minPic50}
                onChange={e => { setMinPic50(parseFloat(e.target.value) || 0); setPage(1); }}
                className="bg-surface-700 border border-white/10 rounded-xl px-3 py-1.5 text-xs text-white w-24 outline-none focus:border-primary-500" />
              <input type="number" placeholder="Max Tox" step="0.1" min="0" max="1" value={maxTox}
                onChange={e => { setMaxTox(parseFloat(e.target.value) || 0); setPage(1); }}
                className="bg-surface-700 border border-white/10 rounded-xl px-3 py-1.5 text-xs text-white w-24 outline-none focus:border-primary-500" />
              <button onClick={() => setRequireLipinski(!requireLipinski)}
                className={`px-3 py-1.5 rounded-xl text-xs font-medium border transition-all ${requireLipinski ? 'bg-accent-500/20 border-accent-500/40 text-accent-300' : 'bg-surface-700/50 border-white/10 text-slate-400'}`}>
                Lipinski Only
              </button>
            </div>
          </div>

          {error && <div className="text-sm text-amber-400 py-2">{error} — Click "Run ADMET Screening" to generate results.</div>}

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-white/10 text-slate-400 uppercase tracking-wider">
                  <th className="py-2.5 px-3">#</th>
                  <th className="py-2.5 px-3">ChEMBL ID</th>
                  <th className="py-2.5 px-3 text-right">pIC50</th>
                  <th className="py-2.5 px-3 text-right">Tox Risk</th>
                  <th className="py-2.5 px-3">Tox Label</th>
                  <th className="py-2.5 px-3 text-right">Log Sol.</th>
                  <th className="py-2.5 px-3">Solubility</th>
                  <th className="py-2.5 px-3">Composite Score</th>
                  <th className="py-2.5 px-3 text-center">Lipinski</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                {admetData?.molecules.map((mol, idx) => (
                  <tr key={mol.molecule_chembl_id} className="hover:bg-white/[0.02] transition-colors">
                    <td className="py-2.5 px-3 font-mono text-slate-500">{(page - 1) * pageSize + idx + 1}</td>
                    <td className="py-2.5 px-3 font-mono text-accent-300 font-semibold">{mol.molecule_chembl_id}</td>
                    <td className="py-2.5 px-3 text-right font-mono font-bold text-success-400">{mol.predicted_pIC50.toFixed(3)}</td>
                    <td className="py-2.5 px-3 text-right font-mono text-slate-300">
                      {mol.tox_probability !== null ? (mol.tox_probability * 100).toFixed(1) + '%' : '—'}
                    </td>
                    <td className="py-2.5 px-3">
                      <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold border ${toxBadge(mol.tox_label)}`}>
                        {mol.tox_label}
                      </span>
                    </td>
                    <td className="py-2.5 px-3 text-right font-mono text-slate-400">
                      {mol.predicted_log_solubility !== null ? mol.predicted_log_solubility.toFixed(2) : '—'}
                    </td>
                    <td className="py-2.5 px-3">
                      <span className={`text-[10px] font-semibold ${solBadge(mol.solubility_label)}`}>
                        {mol.solubility_label}
                      </span>
                    </td>
                    <td className="py-2.5 px-3 w-40">
                      <ScoreBar value={mol.composite_score} color="bg-primary-500" />
                    </td>
                    <td className="py-2.5 px-3 text-center">
                      {mol.lipinski_pass
                        ? <span className="text-success-400 text-[10px] font-bold">PASS</span>
                        : <span className="text-red-400 text-[10px] font-bold">FAIL</span>}
                    </td>
                  </tr>
                )) ?? (
                  <tr><td colSpan={9} className="py-8 text-center text-slate-500">No data — run ADMET screening first.</td></tr>
                )}
              </tbody>
            </table>
          </div>

          {admetData && (
            <div className="flex items-center justify-between pt-3 border-t border-white/5 text-xs text-slate-400">
              <span>Page {page} of {Math.ceil(admetData.total_filtered / pageSize) || 1}</span>
              <div className="flex gap-2">
                <button disabled={page <= 1} onClick={() => setPage(p => p - 1)}
                  className="px-3 py-1.5 rounded-xl bg-surface-700/50 border border-white/5 disabled:opacity-40 hover:border-white/20 transition-colors">
                  Previous
                </button>
                <button disabled={page * pageSize >= admetData.total_filtered} onClick={() => setPage(p => p + 1)}
                  className="px-3 py-1.5 rounded-xl bg-surface-700/50 border border-white/5 disabled:opacity-40 hover:border-white/20 transition-colors">
                  Next
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Disclaimer */}
        <div className="glass-card p-4 border border-amber-500/20 text-center text-xs text-slate-400 space-y-1">
          <p className="font-semibold text-amber-400">⚠️ Scientific Disclaimer</p>
          <p>ADMET predictions and quantum optimization results are computational outputs and do not constitute experimental or clinical validation.</p>
        </div>

      </div>
    </div>
  );
};
