import React, { useState, useEffect } from 'react';
import { Link, useParams, useNavigate } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';
import { experimentsApi, dockingApi } from '../api/client';

interface DockingResultDetail {
  docking_rank: number;
  molecule_chembl_id: string;
  smiles: string;
  predicted_pIC50: number;
  binding_affinity: number | null;
  best_pose_rmsd_lb: number | null;
  best_pose_rmsd_ub: number | null;
  n_poses_returned: number | null;
  status: string;
  mmff_energy_kcal: number | null;
}

interface DockingRunResult {
  status: string;
  docking_run_id?: number;
  experiment_id?: number;
  docking_available: boolean;
  receptor_pdb_id: string;
  total_candidates: number;
  n_successful: number;
  best_affinity: number | null;
  avg_affinity: number | null;
  runtime_seconds: number;
  unavailable: boolean;
  simulated?: boolean;
  blockers: string[];
  results: DockingResultDetail[];
  grid_box: { center: number[]; size: number[]; pdb_id?: string };
  active_residues: string[];
  disclaimer: string;
}

const EGFR_BOX_CENTER = [22.0, 0.5, 52.5];
const EGFR_BOX_SIZE = [20.0, 20.0, 20.0];

const StatusBadge: React.FC<{ status: string }> = ({ status }) => {
  const s = status.toUpperCase();
  const cls =
    s === 'SUCCESS'
      ? 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30'
      : s === 'SIMULATED'
      ? 'bg-purple-500/20 text-purple-300 border-purple-500/30'
      : s === 'UNAVAILABLE' || s === 'NOT_DOCKED'
      ? 'bg-amber-500/20 text-amber-400 border-amber-500/30'
      : 'bg-rose-500/20 text-rose-400 border-rose-500/30';
  return (
    <span className={`px-2 py-0.5 rounded-full text-xs font-semibold border ${cls}`}>
      {s === 'SIMULATED' ? '⚗️ Simulated' : s}
    </span>
  );
};

const DockingPage: React.FC = () => {
  const { token } = useAuthStore();
  const { experimentId } = useParams<{ experimentId: string }>();
  const navigate = useNavigate();
  const expId = Number(experimentId);

  const [experiment, setExperiment] = useState<{ name: string } | null>(null);
  const [result, setResult] = useState<DockingRunResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Config
  const [pdbId, setPdbId] = useState('1M17');
  const [nCandidates, setNCandidates] = useState(15);
  const [exhaustiveness, setExhaustiveness] = useState(8);

  useEffect(() => {
    if (!token) { navigate('/login'); return; }
    experimentsApi.get(expId).then(r => setExperiment(r.data)).catch(() => {});
    dockingApi.get(expId).then(r => setResult(r.data)).catch(() => {});
  }, [expId, token, navigate]);

  const handleRun = async () => {
    setLoading(true);
    setError(null);
    try {
      const resp = await dockingApi.run(expId, {
        pdb_id: pdbId,
        n_candidates: nCandidates,
        exhaustiveness,
        grid_box: null,
      });
      setResult(resp.data);
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setError(msg || 'Docking request failed.');
    } finally {
      setLoading(false);
    }
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
            <span className="text-white text-sm font-medium">Molecular Docking</span>
          </div>
        </div>
      </div>

      <div className="max-w-6xl mx-auto px-6 py-8 space-y-6">
        {/* Title */}
        <div>
          <h1 className="text-3xl font-bold text-white">🔬 Molecular Docking</h1>
          <p className="text-slate-400 mt-1 text-sm">AutoDock Vina — EGFR Kinase Domain (PDB: 1M17)</p>
        </div>

        {/* Config Panel */}
        <div className="bg-surface-800/60 border border-white/8 rounded-2xl p-6">
          <h2 className="text-lg font-semibold text-white mb-4">Docking Configuration</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
            <div>
              <label className="block text-xs text-slate-400 mb-1">PDB ID (receptor)</label>
              <input
                id="dock-pdb-id"
                className="w-full bg-surface-700 border border-white/10 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-accent-500"
                value={pdbId}
                onChange={e => setPdbId(e.target.value.toUpperCase())}
              />
            </div>
            <div>
              <label className="block text-xs text-slate-400 mb-1">Top N candidates</label>
              <input
                id="dock-n-candidates"
                type="number" min={1} max={50}
                className="w-full bg-surface-700 border border-white/10 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-accent-500"
                value={nCandidates}
                onChange={e => setNCandidates(Number(e.target.value))}
              />
            </div>
            <div>
              <label className="block text-xs text-slate-400 mb-1">Exhaustiveness (1–64)</label>
              <input
                id="dock-exhaustiveness"
                type="number" min={1} max={64}
                className="w-full bg-surface-700 border border-white/10 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-accent-500"
                value={exhaustiveness}
                onChange={e => setExhaustiveness(Number(e.target.value))}
              />
            </div>
          </div>

          {/* Grid box info */}
          <div className="bg-surface-700/50 rounded-xl p-4 mb-4 text-xs text-slate-400 grid grid-cols-2 gap-2">
            <span>🎯 Binding site: ATP pocket (Yun et al., 2007)</span>
            <span>Center: [{EGFR_BOX_CENTER.join(', ')}] Å</span>
            <span>Size: [{EGFR_BOX_SIZE.join(', ')}] Å</span>
            <span>Active residues: Lys745, Met793, Thr790…</span>
          </div>

          <button
            id="btn-run-docking"
            onClick={handleRun}
            disabled={loading}
            className="bg-accent-600 hover:bg-accent-500 disabled:opacity-40 text-white font-semibold px-6 py-2.5 rounded-xl transition-colors"
          >
            {loading ? '⏳ Running…' : '🚀 Run Docking'}
          </button>
        </div>

        {error && (
          <div className="bg-rose-500/10 border border-rose-500/30 rounded-xl p-4 text-rose-400 text-sm">{error}</div>
        )}

        {result && (
          <>
            {/* Simulated mode banner */}
            {result.simulated && (
              <div className="bg-purple-500/10 border border-purple-500/30 rounded-2xl p-5 flex items-start gap-4">
                <span className="text-3xl flex-shrink-0">⚗️</span>
                <div className="space-y-1">
                  <div className="flex items-center gap-2 flex-wrap">
                    <h3 className="text-purple-300 font-semibold">Simulated Docking Scores</h3>
                    <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-purple-500/20 text-purple-300 border border-purple-500/30">
                      Physics-Inspired Estimate
                    </span>
                  </div>
                  <p className="text-slate-400 text-xs leading-relaxed max-w-3xl">
                    AutoDock Vina / RDKit are unavailable on this machine. Scores are generated
                    from molecular descriptors (pIC50, MW, logP, SMILES complexity) using a
                    deterministic formula calibrated to the EGFR erlotinib reference range
                    (~−8 to −10 kcal/mol). <strong className="text-purple-300">Not real Vina output.</strong>
                  </p>
                </div>
              </div>
            )}

            {/* Stats grid — shown for both real and simulated */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {[
                { label: result.simulated ? 'Simulated' : 'Docked', value: result.n_successful, unit: 'molecules', color: result.simulated ? 'text-purple-300' : 'text-white' },
                { label: 'Best Affinity', value: result.best_affinity != null ? `${result.best_affinity.toFixed(2)} kcal/mol` : '—', color: 'text-emerald-400' },
                { label: 'Avg Affinity',  value: result.avg_affinity  != null ? `${result.avg_affinity.toFixed(2)}  kcal/mol` : '—', color: 'text-sky-400' },
                { label: 'Runtime',       value: `${result.runtime_seconds.toFixed(2)}s`, color: 'text-white' },
              ].map(({ label, value, unit, color }) => (
                <div key={label} className="bg-surface-800/60 border border-white/8 rounded-xl p-4">
                  <p className="text-slate-400 text-xs">{label}</p>
                  <p className={`font-bold text-xl mt-1 ${color}`}>{value}</p>
                  {unit && <p className="text-slate-500 text-xs">{unit}</p>}
                </div>
              ))}
            </div>

            {/* Results table */}
            <div className="bg-surface-800/60 border border-white/8 rounded-2xl overflow-hidden">
              <div className="px-6 py-4 border-b border-white/5 flex items-center justify-between">
                <div>
                  <h3 className="text-white font-semibold flex items-center gap-2">
                    {result.simulated ? '⚗️ Simulated Docking Results' : '🔬 Docking Results'}
                    {result.simulated && (
                      <span className="text-[10px] font-normal px-1.5 py-0.5 rounded bg-purple-500/15 text-purple-300 border border-purple-500/25">
                        Not real Vina scores
                      </span>
                    )}
                  </h3>
                  <p className="text-slate-500 text-xs mt-0.5">
                    Receptor: {result.receptor_pdb_id} · {result.total_candidates} candidates
                    {result.simulated && ' · sorted by simulated affinity'}
                  </p>
                </div>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-white/5 text-slate-400 text-xs bg-surface-800/40">
                      <th className="px-4 py-3 text-left">#</th>
                      <th className="px-4 py-3 text-left">ChEMBL ID</th>
                      <th className="px-4 py-3 text-right">pred. pIC50</th>
                      <th className="px-4 py-3 text-right">
                        Affinity (kcal/mol)
                        {result.simulated && (
                          <span className="ml-1 text-[9px] text-purple-400 font-normal">simulated</span>
                        )}
                      </th>
                      <th className="px-4 py-3 text-right">RMSD lb</th>
                      <th className="px-4 py-3 text-center">Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.results.map((r, i) => (
                      <tr
                        key={r.molecule_chembl_id}
                        className={`border-b border-white/5 hover:bg-white/3 transition-colors ${
                          i % 2 === 0 ? 'bg-surface-800/20' : ''
                        } ${r.status === 'SIMULATED' && i === 0 ? 'ring-1 ring-inset ring-purple-500/20' : ''}`}
                      >
                        <td className="px-4 py-3 text-slate-400 font-mono">{r.docking_rank}</td>
                        <td className="px-4 py-3 text-white font-medium">{r.molecule_chembl_id}</td>
                        <td className="px-4 py-3 text-right text-sky-400">{r.predicted_pIC50.toFixed(2)}</td>
                        <td className="px-4 py-3 text-right">
                          {r.binding_affinity != null ? (
                            <span className={`font-semibold ${
                              r.status === 'SIMULATED' ? 'text-purple-300' : 'text-emerald-400'
                            }`}>
                              {r.binding_affinity.toFixed(2)}
                            </span>
                          ) : (
                            <span className="text-slate-600">—</span>
                          )}
                        </td>
                        <td className="px-4 py-3 text-right text-slate-400">
                          {r.best_pose_rmsd_lb != null ? r.best_pose_rmsd_lb.toFixed(2) : '—'}
                        </td>
                        <td className="px-4 py-3 text-center">
                          <StatusBadge status={r.status} />
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Disclaimer */}
            <div className="bg-surface-800/30 border border-white/5 rounded-xl p-4 text-slate-500 text-xs leading-relaxed">
              <strong className="text-slate-400">⚠️ Disclaimer:</strong> {result.disclaimer}
            </div>
          </>
        )}
      </div>
    </div>
  );
};

export default DockingPage;
