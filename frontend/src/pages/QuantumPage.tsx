import React, { useState, useEffect, useCallback } from 'react';
import { Link, useParams, useNavigate } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';
import { experimentsApi, quantumApi } from '../api/client';

interface QuantumCandidate {
  rank: number;
  molecule_chembl_id: string;
  smiles: string;
  predicted_pIC50: number;
  tox_probability: number | null;
  predicted_log_solubility: number | null;
  composite_score: number;
  bioactivity_norm: number;
  toxicity_risk_norm: number;
  solubility_norm: number;
  drug_likeness_norm: number;
  lipinski_pass: boolean;
  molecular_weight: number;
  logP: number;
  selected_by_qaoa: boolean;
  selected_by_classical: boolean;
}

interface QuantumResult {
  experiment_id: number;
  optimization_id: number;
  status: string;
  backend: string;
  n_candidates_input: number;
  n_candidates_selected: number;
  qaoa_reps: number;
  qaoa_objective: number;
  classical_objective: number;
  qaoa_runtime_s: number;
  classical_runtime_s: number;
  pipeline: Record<string, number>;
  quantum_config: Record<string, unknown>;
  filter_config: Record<string, unknown>;
  qaoa_unavailable?: boolean;
  qaoa_unavailable_reason?: string;
  qaoa_result: {
    backend: string;
    n_candidates: number;
    k_select: number;
    selected_ids: string[];
    selected_scores: number[];
    qaoa_objective_value: number;
    n_selected: number;
    constraint_satisfied: boolean;
    runtime_seconds: number;
    unavailable?: boolean;
    unavailable_reason?: string;
    circuit_info?: Record<string, unknown>;
  };
  classical_result: {
    algorithm: string;
    selected_ids: string[];
    selected_scores: number[];
    classical_objective_value: number;
    n_selected: number;
    n_combinations_evaluated: number;
    runtime_seconds: number;
  };
  disclaimer: string;
}

// ── Pipeline Step Component ───────────────────────────────────────
const PipelineStep: React.FC<{
  icon: string;
  label: string;
  count: number | string;
  active?: boolean;
  badge?: string;
}> = ({ icon, label, count, active, badge }) => (
  <div
    className={`flex flex-col items-center p-3 rounded-xl border min-w-[105px] text-center transition-all ${
      active
        ? 'bg-surface-800/80 border-accent-500/30 text-white'
        : 'bg-surface-800/40 border-white/5 text-slate-400'
    }`}
  >
    <span className="text-xl mb-1">{icon}</span>
    <span className="text-[11px] font-medium text-slate-300">{label}</span>
    <span className="text-xs font-bold text-accent-400 mt-0.5 font-mono">{count}</span>
    {badge && (
      <span className="mt-1 text-[9px] px-1.5 py-0.2 rounded bg-amber-500/20 text-amber-300 border border-amber-500/30">
        {badge}
      </span>
    )}
  </div>
);

const PipelineArrow: React.FC = () => (
  <div className="flex items-center text-slate-600 px-1 font-bold text-sm select-none">
    →
  </div>
);

// ── Candidate Card ────────────────────────────────────────────────
const CandidateCard: React.FC<{
  cand: QuantumCandidate;
  selectedByQaoa: boolean;
  selectedByClassical: boolean;
  rank: number;
}> = ({ cand, selectedByQaoa, selectedByClassical, rank }) => {
  const isSelected = selectedByQaoa || selectedByClassical;

  return (
    <div
      className={`glass-card p-4 space-y-3 transition-all ${
        isSelected
          ? 'border border-accent-500/40 bg-accent-500/5 shadow-lg shadow-accent-500/5'
          : 'border border-white/5 hover:border-white/15'
      }`}
    >
      <div className="flex items-start justify-between gap-2">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-surface-700 text-slate-400">
              #{rank}
            </span>
            <span className="font-mono text-xs font-bold text-white">
              {cand.molecule_chembl_id}
            </span>
          </div>
          <p className="text-[10px] text-slate-500 font-mono truncate max-w-[180px] mt-0.5" title={cand.smiles}>
            {cand.smiles}
          </p>
        </div>
        <div className="flex flex-col items-end gap-1">
          {selectedByClassical && (
            <span className="text-[9px] font-bold px-1.5 py-0.5 rounded bg-success-500/20 text-success-400 border border-success-500/30">
              Classical Pick
            </span>
          )}
          {selectedByQaoa && (
            <span className="text-[9px] font-bold px-1.5 py-0.5 rounded bg-accent-500/20 text-accent-300 border border-accent-500/30">
              QAOA Pick
            </span>
          )}
          {!isSelected && (
            <span className="text-[9px] px-1.5 py-0.5 rounded bg-surface-700 text-slate-400">
              Screened
            </span>
          )}
        </div>
      </div>

      <div className="text-xs space-y-1">
        {[
          ['pIC50', cand.predicted_pIC50.toFixed(2)],
          ['MW', `${cand.molecular_weight.toFixed(1)} Da`],
          ['logP', cand.logP.toFixed(2)],
          ['Lipinski', cand.lipinski_pass ? 'Pass' : 'Violated'],
          ['Composite', cand.composite_score.toFixed(3)],
        ].map(([k, v]) => (
          <div key={k} className="flex justify-between border-b border-white/5 py-0.5">
            <span className="text-slate-500 text-[11px]">{k}</span>
            <span className="text-slate-200 font-mono text-[11px]">{v}</span>
          </div>
        ))}
      </div>

      <div className="space-y-1 pt-1">
        {[
          { label: 'Bioactivity', value: cand.bioactivity_norm, color: 'bg-primary-500' },
          { label: 'Solubility', value: cand.solubility_norm, color: 'bg-success-500' },
          { label: 'Drug-like', value: cand.drug_likeness_norm, color: 'bg-accent-500' },
          { label: 'Tox Risk ↓', value: cand.toxicity_risk_norm, color: 'bg-red-500' },
        ].map(({ label, value, color }) => (
          <div key={label} className="flex items-center gap-2 text-[10px]">
            <span className="text-slate-500 w-16">{label}</span>
            <div className="flex-1 h-1 bg-surface-700 rounded-full overflow-hidden">
              <div
                className={`h-full ${color} rounded-full`}
                style={{ width: `${Math.max(0, Math.min(100, Math.round(value * 100)))}%` }}
              />
            </div>
            <span className="text-slate-400 font-mono w-8 text-right">
              {(value * 100).toFixed(0)}%
            </span>
          </div>
        ))}
      </div>
    </div>
  );
};

// ── Main Quantum Page ─────────────────────────────────────────────
export const QuantumPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { isAuthenticated } = useAuthStore();

  const [result, setResult] = useState<QuantumResult | null>(null);
  const [candidates, setCandidates] = useState<QuantumCandidate[]>([]);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expName, setExpName] = useState('');
  const [showSelected, setShowSelected] = useState(false);

  // Config sliders
  const [nCandidates, setNCandidates] = useState(10);
  const [kSelect, setKSelect] = useState(5);
  const [qaoa_reps, setQaoaReps] = useState(2);
  const [minPic50, setMinPic50] = useState(5.0);

  useEffect(() => {
    if (!isAuthenticated) navigate('/login');
  }, [isAuthenticated, navigate]);

  const fetchData = useCallback(async () => {
    if (!id) return;
    const expId = parseInt(id, 10);
    try {
      const expRes = await experimentsApi.get(expId);
      setExpName(expRes.data.name ?? `Experiment #${id}`);

      const [qRes, cRes] = await Promise.all([
        quantumApi.get(expId),
        quantumApi.getCandidates(expId),
      ]);
      setResult(qRes.data);
      setCandidates(cRes.data.candidates || []);
    } catch {
      // Not an error — just no result yet
      setError(null);
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleRunQAOA = async () => {
    if (!id) return;
    setRunning(true);
    setError(null);
    try {
      await quantumApi.run(parseInt(id, 10), {
        n_candidates: nCandidates,
        k_select: kSelect,
        qaoa_reps: qaoa_reps,
        min_pic50: minPic50,
        max_tox_risk: 1.0,
        min_log_sol: -10.0,
        require_lipinski: false,
        top_n_admet_input: 100,
      });
      await fetchData();
    } catch (e: unknown) {
      const errData = (e as { response?: { data?: { detail?: string | { msg?: string }[] } } })?.response?.data;
      let msg = 'Quantum optimization failed.';
      if (typeof errData?.detail === 'string') {
        msg = errData.detail;
      } else if (Array.isArray(errData?.detail) && errData.detail[0]?.msg) {
        msg = errData.detail[0].msg;
      }
      setError(msg);
    } finally {
      setRunning(false);
    }
  };

  const displayCandidates = showSelected
    ? candidates.filter((c) => c.selected_by_qaoa || c.selected_by_classical)
    : candidates;

  if (!isAuthenticated) return null;

  const isDegradedMode = result?.qaoa_unavailable || result?.qaoa_result?.unavailable;

  return (
    <div className="min-h-screen pt-16 pl-56">
      <div className="p-8 max-w-7xl space-y-6">

        {/* Breadcrumb */}
        <div className="flex items-center gap-2 text-sm text-slate-500 animate-slide-up">
          <Link to="/experiments" className="hover:text-slate-300 transition-colors">
            Experiments
          </Link>
          <span>/</span>
          <Link to={`/experiments/${id}`} className="hover:text-slate-300 transition-colors">
            {expName || `Experiment #${id}`}
          </Link>
          <span>/</span>
          <span className="text-white font-medium">Quantum Optimization</span>
        </div>

        {/* Header */}
        <div className="flex items-start justify-between gap-4">
          <div>
            <div className="section-divider mb-3" />
            <h1 className="text-2xl font-bold text-white flex items-center gap-2">
              ⚛️ Quantum Optimization (QAOA)
            </h1>
            <p className="text-slate-400 text-sm mt-1">
              QUBO formulation · QAOA Simulator · Classical Exact Solver Comparison
            </p>
          </div>
          <div className="flex items-center gap-3">
            <Link to={`/experiments/${id}/admet`}>
              <button className="px-3 py-2 rounded-xl text-sm text-slate-400 hover:text-white transition-colors">
                ← ADMET
              </button>
            </Link>
            <Link to={`/experiments/${id}`}>
              <button className="px-3 py-2 rounded-xl text-sm text-slate-400 hover:text-white transition-colors">
                ← Experiment
              </button>
            </Link>
          </div>
        </div>

        {/* Scientific Disclaimer Banner */}
        <div className="glass-card p-3 border border-amber-500/20 flex items-start gap-3">
          <span className="text-amber-400 text-base flex-shrink-0 mt-0.5">⚠️</span>
          <p className="text-xs text-slate-400">
            <span className="text-amber-400 font-semibold">Scientific Disclaimer:</span>{' '}
            QAOA runs on a classical statevector simulator (not real quantum hardware). Results do not establish
            quantum advantage. QAOA-based and classical optimization results are shown side-by-side for research comparison only.
          </p>
        </div>

        {/* Degraded Mode Notice (when Qiskit native extension is restricted) */}
        {isDegradedMode && (
          <div className="glass-card p-4 border border-amber-500/40 bg-amber-500/10 rounded-2xl flex items-start gap-3 animate-fade-in">
            <span className="text-amber-400 text-xl flex-shrink-0">⚡</span>
            <div className="space-y-1 text-xs">
              <div className="flex items-center gap-2">
                <h3 className="font-bold text-amber-300">Host Application Control Notice</h3>
                <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-amber-500/20 text-amber-300 border border-amber-500/30">
                  Classical Fallback Active
                </span>
              </div>
              <p className="text-slate-300 leading-relaxed">
                Qiskit binary acceleration is blocked by the Windows Application Control policy on this machine.
                The platform seamlessly fell back to the <strong>Exact Classical Brute-Force Solver</strong>,
                which evaluated all combinatorial possibilities to guarantee the mathematically optimal candidate selection.
              </p>
            </div>
          </div>
        )}

        {/* Configuration Card */}
        <div className="glass-card p-5 space-y-4">
          <h2 className="text-sm font-semibold text-white border-b border-white/10 pb-3 flex items-center gap-2">
            ⚙️ Optimization Configuration
          </h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {[
              { label: 'Candidates (N)', val: nCandidates, setter: setNCandidates, min: 5, max: 25, step: 1 },
              { label: 'Select (K)', val: kSelect, setter: setKSelect, min: 1, max: 10, step: 1 },
              { label: 'QAOA Depth (p)', val: qaoa_reps, setter: setQaoaReps, min: 1, max: 4, step: 1 },
              { label: 'Min pIC50', val: minPic50, setter: setMinPic50, min: 4, max: 10, step: 0.5 },
            ].map(({ label, val, setter, min, max, step }) => (
              <div key={label} className="space-y-1.5">
                <label className="text-[11px] text-slate-400 font-medium">{label}</label>
                <div className="flex items-center gap-2">
                  <input
                    type="range"
                    min={min}
                    max={max}
                    step={step}
                    value={val}
                    onChange={(e) => setter(parseFloat(e.target.value))}
                    className="flex-1 accent-accent-500 cursor-pointer"
                  />
                  <span className="font-mono text-accent-300 text-xs w-10 text-right">{val}</span>
                </div>
              </div>
            ))}
          </div>

          <div className="flex items-center gap-3 pt-2">
            <button
              onClick={handleRunQAOA}
              disabled={running}
              className="px-5 py-2.5 rounded-xl text-sm font-bold bg-gradient-to-r from-accent-500 to-accent-600 hover:from-accent-400 hover:to-accent-500 text-white transition-all shadow-accent-500/25 shadow-md disabled:opacity-50 flex items-center gap-2"
            >
              {running ? '⏳ Running Optimization...' : '⚛️ Run QAOA + Classical Solver'}
            </button>
            <p className="text-xs text-slate-500">
              {nCandidates} candidates → C({nCandidates},{kSelect}) ={' '}
              {Array.from({ length: kSelect }, (_, i) => nCandidates - i).reduce((a, b) => a * b, 1) /
                Array.from({ length: kSelect }, (_, i) => i + 1).reduce((a, b) => a * b, 1)}{' '}
              combinations evaluated classically
            </p>
          </div>

          {error && <p className="text-sm text-red-400 bg-red-500/10 p-3 rounded-xl border border-red-500/20">{error}</p>}
        </div>

        {/* Results View */}
        {result && (
          <>
            {/* Pipeline Flow */}
            <div className="glass-card p-5 space-y-3">
              <h2 className="text-sm font-semibold text-white flex items-center gap-2">
                🔬 Optimization Pipeline
              </h2>
              <div className="flex items-start gap-1 overflow-x-auto pb-2">
                <PipelineStep icon="🧬" label="EGFR Dataset" count={result.pipeline.total_egfr_molecules} active />
                <PipelineArrow />
                <PipelineStep icon="🧪" label="ADMET Screen" count={result.pipeline.admet_input_count} active />
                <PipelineArrow />
                <PipelineStep icon="🎯" label="Filtered" count={result.pipeline.after_filter_count} active />
                <PipelineArrow />
                <PipelineStep icon="📊" label="QUBO Input" count={result.pipeline.quantum_input_count} active />
                <PipelineArrow />
                <PipelineStep
                  icon="⚛️"
                  label="QAOA"
                  count={isDegradedMode ? 'Unavailable' : `${result.qaoa_result.n_selected} sel.`}
                  active={!isDegradedMode}
                  badge={isDegradedMode ? 'Bypassed' : undefined}
                />
                <PipelineArrow />
                <PipelineStep
                  icon="💻"
                  label="Classical"
                  count={`${result.classical_result.n_selected} sel.`}
                  active
                  badge="Optimal"
                />
              </div>
            </div>

            {/* Comparison Cards */}
            <div className="grid md:grid-cols-2 gap-4">
              {/* QAOA Card */}
              <div className="glass-card p-5 border border-accent-500/20 space-y-3">
                <div className="flex items-center justify-between pb-2 border-b border-white/10">
                  <h2 className="text-sm font-bold text-white flex items-center gap-2">
                    ⚛️ QAOA Result
                  </h2>
                  <span
                    className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
                      isDegradedMode
                        ? 'bg-amber-500/15 text-amber-400 border border-amber-500/30'
                        : result.qaoa_result.constraint_satisfied
                        ? 'bg-success-500/15 text-success-400 border border-success-500/30'
                        : 'bg-amber-500/15 text-amber-400 border border-amber-500/30'
                    }`}
                  >
                    {isDegradedMode
                      ? 'Unavailable (Host Policy)'
                      : result.qaoa_result.constraint_satisfied
                      ? 'Constraint Satisfied'
                      : 'Constraint Violated'}
                  </span>
                </div>

                <div className="text-xs space-y-2">
                  {[
                    ['Backend', isDegradedMode ? 'Qiskit Native Blocked' : result.qaoa_result.backend],
                    ['Candidates Input', `${result.qaoa_result.n_candidates}`],
                    ['K Selected', `${result.qaoa_result.n_selected} / ${result.qaoa_result.k_select}`],
                    ['Objective Value', isDegradedMode ? 'N/A' : (result.qaoa_result.qaoa_objective_value?.toFixed(6) ?? '—')],
                    ['Runtime', isDegradedMode ? '0.000s' : `${result.qaoa_result.runtime_seconds.toFixed(3)}s`],
                    ['QAOA Depth (p)', `${result.qaoa_reps}`],
                  ].map(([k, v]) => (
                    <div key={String(k)} className="flex justify-between border-b border-white/5 py-1">
                      <span className="text-slate-500">{k}</span>
                      <span className="text-slate-200 font-mono text-[11px]">{String(v)}</span>
                    </div>
                  ))}
                </div>

                <div>
                  <p className="text-[10px] text-slate-500 mb-1">QAOA Selected IDs</p>
                  {isDegradedMode ? (
                    <p className="text-[11px] text-slate-400 italic">
                      QAOA skipped due to host policy restriction. See classical solver.
                    </p>
                  ) : (
                    <div className="flex flex-wrap gap-1">
                      {result.qaoa_result.selected_ids.map((cid) => (
                        <span
                          key={cid}
                          className="text-[9px] font-mono bg-accent-500/10 text-accent-300 border border-accent-500/20 px-1.5 py-0.5 rounded"
                        >
                          {cid}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              </div>

              {/* Classical Exact Card */}
              <div className="glass-card p-5 border border-success-500/20 space-y-3">
                <div className="flex items-center justify-between pb-2 border-b border-white/10">
                  <h2 className="text-sm font-bold text-white flex items-center gap-2">
                    💻 Classical Exact Solver
                  </h2>
                  <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-success-500/15 text-success-400 border border-success-500/30">
                    Optimal (Global Minimum)
                  </span>
                </div>

                <div className="text-xs space-y-2">
                  {[
                    ['Algorithm', 'Brute-Force Combinatorial Exact'],
                    ['Combinations Evaluated', result.classical_result.n_combinations_evaluated.toLocaleString()],
                    ['K Selected', `${result.classical_result.n_selected} / ${result.classical_result.n_selected}`],
                    ['Objective Value', result.classical_result.classical_objective_value?.toFixed(6) ?? '—'],
                    ['Runtime', `${result.classical_result.runtime_seconds.toFixed(3)}s`],
                    ['Status', 'OPTIMAL (Exact Global Minimum)'],
                  ].map(([k, v]) => (
                    <div key={String(k)} className="flex justify-between border-b border-white/5 py-1">
                      <span className="text-slate-500">{k}</span>
                      <span className="text-slate-200 font-mono text-[11px]">{String(v)}</span>
                    </div>
                  ))}
                </div>

                <div>
                  <p className="text-[10px] text-slate-500 mb-1">Classical Selected IDs</p>
                  <div className="flex flex-wrap gap-1">
                    {result.classical_result.selected_ids.map((cid) => (
                      <span
                        key={cid}
                        className="text-[9px] font-mono bg-success-500/10 text-success-400 border border-success-500/20 px-1.5 py-0.5 rounded"
                      >
                        {cid}
                      </span>
                    ))}
                  </div>
                </div>
              </div>
            </div>

            {/* QUBO Formulation Info */}
            <div className="glass-card p-5 border-l-4 border-l-accent-500 text-xs space-y-2">
              <p className="font-semibold text-white">QUBO Mathematical Formulation</p>
              <code className="text-accent-300 bg-surface-800 px-3 py-2 rounded block font-mono text-[11px] whitespace-pre-wrap">
{`minimize:  −∑ᵢ(scoreᵢ × xᵢ) + λ × (∑ᵢxᵢ − K)²
where:     xᵢ ∈ {0, 1},  K = ${result.quantum_config.k_select ?? kSelect},  λ = 5.0 (penalty coefficient)
scoreᵢ:    composite ADMET-bioactivity score ∈ [0, 1]`}
              </code>
              <p className="text-slate-500">Source: <code>quantum/qubo.py</code> · <code>quantum/classical_solver.py</code></p>
            </div>

            {/* Candidate Pool */}
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h2 className="text-lg font-bold text-white flex items-center gap-2">
                  🎯 QUBO Candidate Pool ({candidates.length} candidates)
                </h2>
                <button
                  onClick={() => setShowSelected(!showSelected)}
                  className={`px-3 py-1.5 rounded-xl text-xs font-medium border transition-all ${
                    showSelected
                      ? 'bg-accent-500/20 border-accent-500/40 text-accent-300'
                      : 'bg-surface-700/50 border-white/10 text-slate-400 hover:text-white'
                  }`}
                >
                  {showSelected ? 'Show All' : 'Selected Only'}
                </button>
              </div>

              <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
                {displayCandidates.map((cand) => (
                  <CandidateCard
                    key={cand.molecule_chembl_id}
                    cand={cand}
                    selectedByQaoa={cand.selected_by_qaoa}
                    selectedByClassical={cand.selected_by_classical}
                    rank={cand.rank}
                  />
                ))}
              </div>
            </div>
          </>
        )}

        {/* Next Steps — shown when results are available */}
        {result && (
          <div className="glass-card p-6">
            <h3 className="text-white font-semibold mb-3">Next Steps</h3>
            <div className="flex flex-wrap gap-3">
              <Link to={`/experiments/${id}/docking`}>
                <button className="px-4 py-2.5 rounded-xl text-sm bg-teal-500/15 text-teal-300 border border-teal-500/30 hover:bg-teal-500/25 transition-all flex items-center gap-2">
                  🔬 Molecular Docking
                  <span className="text-teal-500 text-xs">→</span>
                </button>
              </Link>
              <Link to={`/experiments/${id}/ranking`}>
                <button className="px-4 py-2.5 rounded-xl text-sm bg-yellow-500/15 text-yellow-300 border border-yellow-500/30 hover:bg-yellow-500/25 transition-all flex items-center gap-2">
                  🏆 Final Rankings
                  <span className="text-yellow-500 text-xs">→</span>
                </button>
              </Link>
            </div>
          </div>
        )}

        {/* Empty State */}
        {!result && !loading && (
          <div className="glass-card p-12 text-center space-y-4">
            <div className="text-5xl">⚛️</div>
            <h2 className="text-xl font-bold text-white">No Quantum Optimization Run Yet</h2>
            <p className="text-slate-400 text-sm max-w-lg mx-auto">
              Configure the parameters above and click "Run QAOA + Classical Solver" to evaluate drug candidate selection.
              Make sure ADMET screening has completed for this experiment.
            </p>
            <Link to={`/experiments/${id}/admet`}>
              <button className="px-4 py-2 rounded-xl text-sm bg-primary-500/20 text-primary-400 border border-primary-500/30 hover:bg-primary-500/30 transition-all">
                ← Run ADMET Screening First
              </button>
            </Link>
          </div>
        )}
      </div>
    </div>
  );
};
export default QuantumPage;
