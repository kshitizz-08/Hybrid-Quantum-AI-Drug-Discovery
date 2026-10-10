import React, { useState, useEffect, useCallback } from 'react';
import { Link, useParams, useNavigate } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';
import { experimentsApi, rankingApi } from '../api/client';

interface RankedCandidate {
  rank: number;
  molecule_chembl_id: string;
  smiles: string;
  predicted_pIC50: number;
  tox_probability: number;
  predicted_log_solubility: number;
  composite_score: number;
  lipinski_pass: boolean;
  molecular_weight: number;
  logP: number;
  bioactivity_score_norm: number;
  drug_likeness_score_norm: number;
  toxicity_score_norm: number;
  solubility_score_norm: number;
  quantum_score_norm: number;
  docking_score_norm: number | null;
  docking_affinity_kcal: number | null;
  final_score: number;
  filtering_reasons: string[];
}

interface RankingResult {
  status: string;
  n_candidates_ranked: number;
  docking_available: boolean;
  validation_report: { total_rows: number; issues: string[]; valid_rows: number };
  weights_used: Record<string, number>;
  methodology_notes: string[];
  dataset_info: {
    source_dataset: string;
    bioactivity_model: string;
    toxicity_model: string;
    limitations: string[];
  };
  candidates: RankedCandidate[];
  runtime_seconds: number;
  disclaimer: string;
  total?: number;
}

const ScoreBar: React.FC<{ value: number; color?: string }> = ({ value, color = 'bg-accent-500' }) => (
  <div className="flex items-center gap-2">
    <div className="flex-1 bg-surface-700 rounded-full h-1.5">
      <div className={`${color} h-1.5 rounded-full transition-all`} style={{ width: `${value * 100}%` }} />
    </div>
    <span className="text-xs text-slate-400 w-8 text-right">{(value * 100).toFixed(0)}%</span>
  </div>
);

const MedalIcon: React.FC<{ rank: number }> = ({ rank }) => {
  if (rank === 1) return <span title="Gold">🥇</span>;
  if (rank === 2) return <span title="Silver">🥈</span>;
  if (rank === 3) return <span title="Bronze">🥉</span>;
  return <span className="text-slate-500 text-xs font-mono w-5 inline-block text-center">#{rank}</span>;
};

const RankingPage: React.FC = () => {
  const { token } = useAuthStore();
  const { experimentId } = useParams<{ experimentId: string }>();
  const navigate = useNavigate();
  const expId = Number(experimentId);

  const [experiment, setExperiment] = useState<{ name: string } | null>(null);
  const [result, setResult] = useState<RankingResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showMethodology, setShowMethodology] = useState(false);
  const [expandedRow, setExpandedRow] = useState<string | null>(null);
  const [includeDocking, setIncludeDocking] = useState(false);

  const loadCached = useCallback(() => {
    rankingApi.get(expId, { limit: 100 })
      .then(r => setResult(r.data))
      .catch(() => {});
  }, [expId]);

  useEffect(() => {
    if (!token) { navigate('/login'); return; }
    experimentsApi.get(expId).then(r => setExperiment(r.data)).catch(() => {});
    loadCached();
  }, [expId, token, navigate, loadCached]);

  const handleCompute = async () => {
    setLoading(true);
    setError(null);
    try {
      const resp = await rankingApi.compute(expId, { include_docking: includeDocking });
      setResult(resp.data);
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setError(msg || 'Ranking computation failed.');
    } finally {
      setLoading(false);
    }
  };

  const handleDownloadCsv = async () => {
    try {
      const resp = await rankingApi.downloadCsv(expId);
      const url = window.URL.createObjectURL(new Blob([resp.data as BlobPart]));
      const a = document.createElement('a');
      a.href = url;
      a.download = `egfr_ranked_candidates_exp${expId}.csv`;
      a.click();
      window.URL.revokeObjectURL(url);
    } catch {
      setError('CSV download failed.');
    }
  };

  const weightColors: Record<string, string> = {
    bioactivity:   'bg-sky-500',
    drug_likeness: 'bg-violet-500',
    toxicity:      'bg-emerald-500',
    solubility:    'bg-teal-500',
    quantum:       'bg-purple-500',
    docking:       'bg-orange-500',
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-surface-950 via-surface-900 to-surface-950">
      {/* Header */}
      <div className="border-b border-white/5 bg-surface-900/70 backdrop-blur-sm px-6 py-4">
        <div className="max-w-6xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Link to="/dashboard" className="text-slate-400 hover:text-white transition-colors text-sm">← Dashboard</Link>
            <span className="text-slate-600">/</span>
            <Link to={`/experiments/${expId}`} className="text-slate-400 hover:text-white transition-colors text-sm">
              {experiment?.name || `Experiment #${expId}`}
            </Link>
            <span className="text-slate-600">/</span>
            <span className="text-white text-sm font-medium">Final Ranking</span>
          </div>
          {result && (
            <button
              id="btn-download-csv"
              onClick={handleDownloadCsv}
              className="text-sm text-slate-400 hover:text-white border border-white/10 hover:border-white/20 px-3 py-1.5 rounded-lg transition-colors flex items-center gap-2"
            >
              ⬇️ Export CSV
            </button>
          )}
        </div>
      </div>

      <div className="max-w-6xl mx-auto px-6 py-8 space-y-6">
        {/* Title */}
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-3xl font-bold text-white">🏆 Final Candidate Ranking</h1>
            <p className="text-slate-400 mt-1 text-sm">Weighted composite scores across AI, ADMET, quantum, and docking components</p>
          </div>
          <button
            onClick={() => setShowMethodology(!showMethodology)}
            className="text-xs text-accent-400 hover:text-accent-300 border border-accent-500/30 hover:border-accent-500/50 px-3 py-1.5 rounded-lg transition-colors"
          >
            {showMethodology ? '▾' : '▸'} Methodology
          </button>
        </div>

        {/* Methodology panel */}
        {showMethodology && result && (
          <div className="bg-surface-800/40 border border-white/8 rounded-2xl p-6 text-sm space-y-3">
            <h3 className="text-white font-semibold">Ranking Methodology</h3>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
              {Object.entries(result.weights_used).map(([k, v]) => (
                v > 0 && (
                  <div key={k} className="bg-surface-700/50 rounded-xl p-3">
                    <div className="flex justify-between mb-1">
                      <span className="text-slate-300 text-xs capitalize">{k.replace('_', ' ')}</span>
                      <span className="text-white text-xs font-bold">{(v * 100).toFixed(0)}%</span>
                    </div>
                    <div className="bg-surface-700 rounded-full h-1">
                      <div className={`${weightColors[k] || 'bg-slate-500'} h-1 rounded-full`} style={{ width: `${v * 100}%` }} />
                    </div>
                  </div>
                )
              ))}
            </div>
            {result.methodology_notes.map((n, i) => (
              <p key={i} className="text-amber-300/70 text-xs bg-amber-500/5 rounded-lg px-3 py-2">⚠️ {n}</p>
            ))}
            <div className="text-slate-400 text-xs space-y-1">
              <p><strong className="text-slate-300">Bioactivity model:</strong> {result.dataset_info.bioactivity_model}</p>
              <p><strong className="text-slate-300">Toxicity model:</strong> {result.dataset_info.toxicity_model}</p>
            </div>
            <details className="text-slate-500 text-xs">
              <summary className="cursor-pointer text-slate-400 hover:text-slate-300">Known limitations</summary>
              <ul className="mt-2 space-y-1 ml-4">
                {result.dataset_info.limitations.map((l, i) => (
                  <li key={i}>• {l}</li>
                ))}
              </ul>
            </details>
          </div>
        )}

        {/* Compute panel */}
        <div className="bg-surface-800/60 border border-white/8 rounded-2xl p-6">
          <h2 className="text-lg font-semibold text-white mb-3">Compute Rankings</h2>
          <div className="flex items-center gap-4 mb-4">
            <label className="flex items-center gap-2 text-sm text-slate-300 cursor-pointer">
              <input
                type="checkbox"
                id="include-docking-checkbox"
                checked={includeDocking}
                onChange={e => setIncludeDocking(e.target.checked)}
                className="accent-accent-500"
              />
              Include docking data (if available)
            </label>
          </div>
          <button
            id="btn-compute-ranking"
            onClick={handleCompute}
            disabled={loading}
            className="bg-accent-600 hover:bg-accent-500 disabled:opacity-40 text-white font-semibold px-6 py-2.5 rounded-xl transition-colors"
          >
            {loading ? '⏳ Computing…' : '🏆 Compute Final Rankings'}
          </button>
        </div>

        {error && (
          <div className="bg-rose-500/10 border border-rose-500/30 rounded-xl p-4 text-rose-400 text-sm">{error}</div>
        )}

        {result && (
          <>
            {/* Stats */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {[
                { label: 'Candidates Ranked', value: result.n_candidates_ranked, icon: '🧬' },
                { label: 'Top Score', value: result.candidates[0]?.final_score.toFixed(3) ?? '—', icon: '🥇' },
                { label: 'Docking Data', value: result.docking_available ? 'Included' : 'Unavailable', icon: '🔬' },
                { label: 'Runtime', value: `${result.runtime_seconds.toFixed(2)}s`, icon: '⏱️' },
              ].map(({ label, value, icon }) => (
                <div key={label} className="bg-surface-800/60 border border-white/8 rounded-xl p-4">
                  <p className="text-slate-400 text-xs">{icon} {label}</p>
                  <p className="text-white font-bold text-xl mt-1">{value}</p>
                </div>
              ))}
            </div>

            {/* Validation */}
            {result.validation_report.issues.length > 0 && (
              <div className="bg-amber-500/10 border border-amber-500/30 rounded-xl p-4">
                <p className="text-amber-400 text-sm font-medium mb-1">Validation Issues</p>
                {result.validation_report.issues.map((issue, i) => (
                  <p key={i} className="text-amber-300/70 text-xs">• {issue}</p>
                ))}
              </div>
            )}

            {/* Candidate table */}
            <div className="bg-surface-800/60 border border-white/8 rounded-2xl overflow-hidden">
              <div className="px-6 py-4 border-b border-white/5 flex justify-between items-center">
                <div>
                  <h3 className="text-white font-semibold">Ranked Candidates</h3>
                  <p className="text-slate-500 text-xs mt-0.5">{result.n_candidates_ranked} molecules · sorted by final weighted score</p>
                </div>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-white/5 text-slate-400 text-xs bg-surface-800/40">
                      <th className="px-4 py-3 text-left">Rank</th>
                      <th className="px-4 py-3 text-left">ChEMBL ID</th>
                      <th className="px-4 py-3 text-right">pIC50</th>
                      <th className="px-4 py-3 text-right">Tox %</th>
                      <th className="px-4 py-3 text-right">MW</th>
                      <th className="px-4 py-3 text-center">Lipinski</th>
                      <th className="px-4 py-3 text-right">Final Score</th>
                      <th className="px-4 py-3 text-center">Details</th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.candidates.map((c, i) => (
                      <React.Fragment key={c.molecule_chembl_id}>
                        <tr
                          className={`border-b border-white/5 hover:bg-white/3 transition-colors cursor-pointer ${i % 2 === 0 ? 'bg-surface-800/10' : ''}`}
                          onClick={() => setExpandedRow(expandedRow === c.molecule_chembl_id ? null : c.molecule_chembl_id)}
                        >
                          <td className="px-4 py-3">
                            <MedalIcon rank={c.rank} />
                          </td>
                          <td className="px-4 py-3 text-white font-medium">{c.molecule_chembl_id}</td>
                          <td className="px-4 py-3 text-right text-sky-400 font-semibold">{c.predicted_pIC50.toFixed(2)}</td>
                          <td className="px-4 py-3 text-right">
                            <span className={c.tox_probability > 0.5 ? 'text-rose-400' : 'text-emerald-400'}>
                              {(c.tox_probability * 100).toFixed(1)}%
                            </span>
                          </td>
                          <td className="px-4 py-3 text-right text-slate-300">{c.molecular_weight.toFixed(0)}</td>
                          <td className="px-4 py-3 text-center">
                            {c.lipinski_pass
                              ? <span className="text-emerald-400">✓</span>
                              : <span className="text-rose-400">✗</span>}
                          </td>
                          <td className="px-4 py-3 text-right">
                            <div className="flex items-center justify-end gap-2">
                              <div className="w-20 bg-surface-700 rounded-full h-1.5">
                                <div
                                  className="bg-gradient-to-r from-accent-600 to-accent-400 h-1.5 rounded-full"
                                  style={{ width: `${c.final_score * 100}%` }}
                                />
                              </div>
                              <span className="text-white font-bold text-xs w-10 text-right">{c.final_score.toFixed(3)}</span>
                            </div>
                          </td>
                          <td className="px-4 py-3 text-center text-slate-500 text-xs">
                            {expandedRow === c.molecule_chembl_id ? '▾' : '▸'}
                          </td>
                        </tr>
                        {expandedRow === c.molecule_chembl_id && (
                          <tr className="bg-surface-800/40 border-b border-white/5">
                            <td colSpan={8} className="px-6 py-4">
                              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                                {/* Component scores */}
                                <div>
                                  <p className="text-slate-400 text-xs font-semibold mb-3 uppercase tracking-wider">Component Scores</p>
                                  <div className="space-y-2">
                                    {[
                                      { label: 'Bioactivity', val: c.bioactivity_score_norm, color: 'bg-sky-500' },
                                      { label: 'Drug-likeness', val: c.drug_likeness_score_norm, color: 'bg-violet-500' },
                                      { label: 'Toxicity safety', val: c.toxicity_score_norm, color: 'bg-emerald-500' },
                                      { label: 'Solubility', val: c.solubility_score_norm, color: 'bg-teal-500' },
                                      { label: 'Quantum', val: c.quantum_score_norm, color: 'bg-purple-500' },
                                    ].map(({ label, val, color }) => (
                                      <div key={label} className="flex items-center gap-2">
                                        <span className="text-slate-400 text-xs w-28">{label}</span>
                                        <ScoreBar value={val} color={color} />
                                      </div>
                                    ))}
                                    <div className="flex items-center gap-2">
                                      <span className="text-slate-400 text-xs w-28">Docking</span>
                                      {c.docking_score_norm != null
                                        ? <ScoreBar value={c.docking_score_norm} color="bg-orange-500" />
                                        : <span className="text-slate-600 text-xs">Unavailable</span>}
                                    </div>
                                  </div>
                                </div>
                                {/* Molecular properties */}
                                <div>
                                  <p className="text-slate-400 text-xs font-semibold mb-3 uppercase tracking-wider">Molecular Properties</p>
                                  <div className="space-y-1 text-xs">
                                    {[
                                      ['SMILES', c.smiles.length > 50 ? c.smiles.slice(0, 50) + '…' : c.smiles] as string[],
                                      ['Molecular Weight', `${c.molecular_weight.toFixed(1)} Da`] as string[],
                                      ['LogP', c.logP.toFixed(2)] as string[],
                                      ['Log Solubility', `${c.predicted_log_solubility.toFixed(2)} mol/L`] as string[],
                                      ['Composite Score', c.composite_score.toFixed(4)] as string[],
                                      ...(c.docking_affinity_kcal != null ? [['Docking Affinity', `${c.docking_affinity_kcal.toFixed(2)} kcal/mol`] as string[]] : []),
                                    ].map(([k, v]) => (
                                      <div key={String(k)} className="flex justify-between">
                                        <span className="text-slate-500">{k}</span>
                                        <span className="text-slate-300 font-mono text-right max-w-xs truncate">{String(v)}</span>
                                      </div>
                                    ))}
                                  </div>
                                  {c.filtering_reasons.length > 0 && (
                                    <div className="mt-3">
                                      <p className="text-amber-400 text-xs font-semibold mb-1">Notes</p>
                                      {c.filtering_reasons.map((r, ri) => (
                                        <p key={ri} className="text-amber-300/70 text-xs">• {r}</p>
                                      ))}
                                    </div>
                                  )}
                                </div>
                              </div>
                            </td>
                          </tr>
                        )}
                      </React.Fragment>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Disclaimer */}
            <div className="bg-surface-800/30 border border-white/5 rounded-xl p-4 text-slate-500 text-xs leading-relaxed">
              <strong className="text-slate-400">⚠️ Scientific Disclaimer:</strong> {result.disclaimer}
            </div>
          </>
        )}
      </div>
    </div>
  );
};

export default RankingPage;
