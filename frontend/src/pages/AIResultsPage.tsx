import React, { useState, useEffect, useCallback } from 'react';
import { Link, useParams, useNavigate } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';
import { experimentsApi, pipelineApi } from '../api/client';
import type {
  ExperimentWithTarget,
  ModelComparisonResponse,
  PreprocessingReportData,
  MoleculePredictionItem,
} from '../types';
import { Button } from '../components/ui/Button';
import { Badge, StatusBadge } from '../components/ui/Badge';

export const AIResultsPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { isAuthenticated } = useAuthStore();

  const [experiment, setExperiment] = useState<ExperimentWithTarget | null>(null);
  const [report, setReport] = useState<PreprocessingReportData | null>(null);
  const [modelMetrics, setModelMetrics] = useState<ModelComparisonResponse | null>(null);
  const [selectedModel, setSelectedModel] = useState<'RandomForest' | 'XGBoost'>('RandomForest');

  // Prediction state & filters
  const [predictions, setPredictions] = useState<MoleculePredictionItem[]>([]);
  const [totalCount, setTotalCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [predicting, setPredicting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Filter params
  const [search, setSearch] = useState('');
  const [minPic50, setMinPic50] = useState<number | ''>('');
  const [onlyLipinski, setOnlyLipinski] = useState(false);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(25);

  useEffect(() => {
    if (!isAuthenticated) navigate('/login');
  }, [isAuthenticated, navigate]);

  const loadData = useCallback(async () => {
    if (!id) return;
    const expId = parseInt(id, 10);
    setLoading(true);
    setError(null);

    try {
      // 1. Get experiment
      const expRes = await experimentsApi.get(expId);
      setExperiment(expRes.data);

      // 2. Get preprocessing report
      try {
        const repRes = await pipelineApi.getPreprocessReport(expId);
        setReport(repRes.data);
      } catch {
        // Report not ready yet
      }

      // 3. Get model metrics
      try {
        const metRes = await pipelineApi.getModelMetrics(expId);
        setModelMetrics(metRes.data);
        if (metRes.data.best_model_by_r2) {
          setSelectedModel(metRes.data.best_model_by_r2 as 'RandomForest' | 'XGBoost');
        }
      } catch {
        // Metrics not ready yet
      }
    } catch {
      setError('Failed to load experiment data.');
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // Load predictions when model, page, or filters change
  const fetchPredictions = useCallback(async () => {
    if (!id) return;
    const expId = parseInt(id, 10);
    try {
      const res = await pipelineApi.getPredictions(expId, {
        model_name: selectedModel,
        limit: pageSize,
        offset: (page - 1) * pageSize,
        min_pIC50: minPic50 !== '' ? minPic50 : undefined,
        search: search.trim() ? search.trim() : undefined,
      });

      let items: MoleculePredictionItem[] = res.data.predictions;
      if (onlyLipinski) {
        items = items.filter(m => m.lipinski_pass);
      }

      setPredictions(items);
      setTotalCount(res.data.total_molecules);
    } catch {
      // Predictions not available yet
      setPredictions([]);
      setTotalCount(0);
    }
  }, [id, selectedModel, page, pageSize, minPic50, search, onlyLipinski]);

  useEffect(() => {
    fetchPredictions();
  }, [fetchPredictions]);

  const handleRunPredict = async () => {
    if (!id) return;
    const expId = parseInt(id, 10);
    setPredicting(true);
    try {
      await pipelineApi.predict(expId, selectedModel);
      await loadData();
      await fetchPredictions();
    } catch {
      alert('Prediction failed. Make sure models are trained.');
    } finally {
      setPredicting(false);
    }
  };

  if (!isAuthenticated) return null;

  return (
    <div className="min-h-screen pt-16 pl-56">
      <div className="p-8 max-w-7xl space-y-6">

        {/* Breadcrumb */}
        <div className="flex items-center gap-2 text-sm text-slate-500 animate-slide-up">
          <Link to="/experiments" className="hover:text-slate-300 transition-colors">Experiments</Link>
          <span>/</span>
          <Link to={`/experiments/${id}`} className="hover:text-slate-300 transition-colors">
            {experiment?.name ?? `Experiment #${id}`}
          </Link>
          <span>/</span>
          <span className="text-white font-medium">AI & Preprocessing Results</span>
        </div>

        {/* Header */}
        <div className="flex items-start justify-between gap-4">
          <div>
            <div className="section-divider mb-3" />
            <h1 className="text-2xl font-bold text-white">AI Screening & Preprocessing Results</h1>
            <p className="text-slate-400 text-sm mt-1">
              EGFR ChEMBL Bioactivity Dataset · RDKit Molecular Descriptors · Random Forest & XGBoost
            </p>
          </div>
          <div className="flex items-center gap-3">
            <Button
              size="sm"
              onClick={handleRunPredict}
              loading={predicting}
            >
              ⚡ Run AI Prediction ({selectedModel})
            </Button>
            <Link to={`/experiments/${id}`}>
              <Button variant="ghost" size="sm">← Back</Button>
            </Link>
          </div>
        </div>

        {/* Error notification */}
        {error && (
          <div className="glass-card p-4 border border-red-500/20 text-red-400 text-sm">
            {error}
          </div>
        )}

        {/* Overview cards grid */}
        <div className="grid lg:grid-cols-3 gap-6">

          {/* Card 1: Data Provenance & Preprocessing */}
          <div className="glass-card p-5 space-y-4">
            <div className="flex items-center justify-between border-b border-white/5 pb-3">
              <h2 className="text-sm font-semibold text-white flex items-center gap-2">
                <span>⚗️</span> Dataset Preprocessing
              </h2>
              <Badge variant="primary">ChEMBL 33</Badge>
            </div>

            {report ? (
              <div className="space-y-3 text-xs">
                <div className="flex justify-between py-1 border-b border-white/5">
                  <span className="text-slate-400">Raw ChEMBL Records</span>
                  <span className="font-mono text-white font-semibold">{report.initial_records.toLocaleString()}</span>
                </div>
                <div className="flex justify-between py-1 border-b border-white/5">
                  <span className="text-slate-400">Non-nM Units Removed</span>
                  <span className="font-mono text-amber-400">-{report.removed.non_nM_units || 0}</span>
                </div>
                <div className="flex justify-between py-1 border-b border-white/5">
                  <span className="text-slate-400">Validity Errors Removed</span>
                  <span className="font-mono text-amber-400">-{report.removed.data_validity_errors || 0}</span>
                </div>
                <div className="flex justify-between py-1 border-b border-white/5">
                  <span className="text-slate-400">Missing SMILES Removed</span>
                  <span className="font-mono text-amber-400">-{report.removed.missing_smiles || 0}</span>
                </div>
                <div className="flex justify-between py-1 border-b border-white/5">
                  <span className="text-slate-400">Duplicates Collapsed (Median)</span>
                  <span className="font-mono text-amber-400">-{report.removed.duplicate_measurements || 0}</span>
                </div>
                <div className="flex justify-between py-1 pt-2 font-bold">
                  <span className="text-success-400">Final Clean Molecules</span>
                  <span className="font-mono text-success-400 text-sm">{report.final_records.toLocaleString()}</span>
                </div>
              </div>
            ) : (
              <p className="text-xs text-slate-500">Run preprocessing to see audit metrics.</p>
            )}
          </div>

          {/* Card 2: Model Comparison */}
          <div className="glass-card p-5 space-y-4">
            <div className="flex items-center justify-between border-b border-white/5 pb-3">
              <h2 className="text-sm font-semibold text-white flex items-center gap-2">
                <span>🤖</span> Model Comparison
              </h2>
              <span className="text-[10px] text-slate-500 font-mono">Held-out Test Set</span>
            </div>

            {modelMetrics ? (
              <div className="space-y-3">
                <table className="w-full text-xs text-left">
                  <thead>
                    <tr className="border-b border-white/10 text-slate-400">
                      <th className="py-1">Metric</th>
                      <th className="py-1 text-right">Random Forest</th>
                      <th className="py-1 text-right">XGBoost</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-white/5 font-mono">
                    <tr>
                      <td className="py-1.5 text-slate-300 font-sans">MAE (Lower is better)</td>
                      <td className="py-1.5 text-right text-accent-300 font-bold">
                        {modelMetrics.models.RandomForest.test_metrics.MAE?.toFixed(4) ?? '—'}
                      </td>
                      <td className="py-1.5 text-right text-slate-300">
                        {modelMetrics.models.XGBoost.test_metrics.MAE?.toFixed(4) ?? '—'}
                      </td>
                    </tr>
                    <tr>
                      <td className="py-1.5 text-slate-300 font-sans">RMSE</td>
                      <td className="py-1.5 text-right text-accent-300">
                        {modelMetrics.models.RandomForest.test_metrics.RMSE?.toFixed(4) ?? '—'}
                      </td>
                      <td className="py-1.5 text-right text-slate-300">
                        {modelMetrics.models.XGBoost.test_metrics.RMSE?.toFixed(4) ?? '—'}
                      </td>
                    </tr>
                    <tr>
                      <td className="py-1.5 text-slate-300 font-sans">R² Score (Higher is better)</td>
                      <td className="py-1.5 text-right text-success-400 font-bold">
                        {modelMetrics.models.RandomForest.test_metrics.R2?.toFixed(4) ?? '—'}
                      </td>
                      <td className="py-1.5 text-right text-slate-300">
                        {modelMetrics.models.XGBoost.test_metrics.R2?.toFixed(4) ?? '—'}
                      </td>
                    </tr>
                  </tbody>
                </table>
                <div className="p-2 rounded bg-success-500/10 border border-success-500/20 text-[11px] text-success-300 flex justify-between">
                  <span>Best Model (by R²):</span>
                  <span className="font-bold">{modelMetrics.best_model_by_r2}</span>
                </div>
              </div>
            ) : (
              <p className="text-xs text-slate-500">Model metrics will appear after training.</p>
            )}
          </div>

          {/* Card 3: Model Selector & Settings */}
          <div className="glass-card p-5 space-y-4">
            <div className="border-b border-white/5 pb-3">
              <h2 className="text-sm font-semibold text-white flex items-center gap-2">
                <span>⚙️</span> Active Inference Settings
              </h2>
            </div>
            <div className="space-y-3">
              <div>
                <label className="block text-xs text-slate-400 mb-1">Select Prediction Model</label>
                <div className="grid grid-cols-2 gap-2">
                  <button
                    onClick={() => setSelectedModel('RandomForest')}
                    className={`px-3 py-2 rounded-xl text-xs font-semibold border transition-all ${
                      selectedModel === 'RandomForest'
                        ? 'bg-primary-500/20 border-primary-500/50 text-white'
                        : 'bg-surface-700/50 border-white/5 text-slate-400 hover:text-white'
                    }`}
                  >
                    Random Forest
                  </button>
                  <button
                    onClick={() => setSelectedModel('XGBoost')}
                    className={`px-3 py-2 rounded-xl text-xs font-semibold border transition-all ${
                      selectedModel === 'XGBoost'
                        ? 'bg-primary-500/20 border-primary-500/50 text-white'
                        : 'bg-surface-700/50 border-white/5 text-slate-400 hover:text-white'
                    }`}
                  >
                    XGBoost
                  </button>
                </div>
              </div>

              <div className="text-[11px] text-slate-400 space-y-1 bg-surface-800/40 p-3 rounded-xl border border-white/5">
                <p>• Features: 8 RDKit descriptors + Morgan FP (radius=2, 2048-bit)</p>
                <p>• Split: Molecule-level 70% Train / 15% Val / 15% Test</p>
                <p>• Target: pIC50 = 9 - log10(IC50_nM)</p>
              </div>
            </div>
          </div>

        </div>

        {/* Predictions Candidate Table Section */}
        <div className="glass-card p-6 space-y-4">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-white/10 pb-4">
            <div>
              <h2 className="text-lg font-bold text-white flex items-center gap-2">
                <span>🏆</span> Prioritized Candidate Molecules
              </h2>
              <p className="text-xs text-slate-400">
                Displaying {predictions.length} of {totalCount.toLocaleString()} candidates predicted by {selectedModel}
              </p>
            </div>

            {/* Filter controls */}
            <div className="flex flex-wrap items-center gap-3">
              {/* Search input */}
              <input
                type="text"
                placeholder="Search ChEMBL ID or SMILES..."
                value={search}
                onChange={e => { setSearch(e.target.value); setPage(1); }}
                className="bg-surface-700 border border-white/10 rounded-xl px-3 py-1.5 text-xs text-white placeholder-slate-500 outline-none focus:border-primary-500"
              />

              {/* Min pIC50 filter */}
              <input
                type="number"
                step="0.5"
                placeholder="Min pIC50 (e.g. 7.0)"
                value={minPic50}
                onChange={e => { setMinPic50(e.target.value ? parseFloat(e.target.value) : ''); setPage(1); }}
                className="w-32 bg-surface-700 border border-white/10 rounded-xl px-3 py-1.5 text-xs text-white placeholder-slate-500 outline-none focus:border-primary-500"
              />

              {/* Lipinski toggle */}
              <button
                onClick={() => setOnlyLipinski(!onlyLipinski)}
                className={`px-3 py-1.5 rounded-xl text-xs font-medium border transition-all ${
                  onlyLipinski
                    ? 'bg-accent-500/20 border-accent-500/40 text-accent-300'
                    : 'bg-surface-700/50 border-white/10 text-slate-400'
                }`}
              >
                Lipinski Only
              </button>
            </div>
          </div>

          {/* Table */}
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-white/10 text-slate-400 uppercase tracking-wider font-semibold">
                  <th className="py-2.5 px-3">#</th>
                  <th className="py-2.5 px-3">Molecule ChEMBL ID</th>
                  <th className="py-2.5 px-3">SMILES</th>
                  <th className="py-2.5 px-3 text-right">Actual pIC50</th>
                  <th className="py-2.5 px-3 text-right">Pred. pIC50</th>
                  <th className="py-2.5 px-3 text-right">Bioactivity Score</th>
                  <th className="py-2.5 px-3 text-right">MW</th>
                  <th className="py-2.5 px-3 text-right">LogP</th>
                  <th className="py-2.5 px-3 text-center">Lipinski</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                {predictions.length > 0 ? (
                  predictions.map((mol, idx) => (
                    <tr key={mol.molecule_chembl_id} className="hover:bg-white/[0.02] transition-colors">
                      <td className="py-2.5 px-3 font-mono text-slate-500">{(page - 1) * pageSize + idx + 1}</td>
                      <td className="py-2.5 px-3 font-mono text-accent-300 font-semibold">{mol.molecule_chembl_id}</td>
                      <td className="py-2.5 px-3 font-mono text-slate-400 max-w-xs truncate" title={mol.smiles}>
                        {mol.smiles}
                      </td>
                      <td className="py-2.5 px-3 text-right font-mono text-slate-300">{mol.pIC50.toFixed(2)}</td>
                      <td className="py-2.5 px-3 text-right font-mono font-bold text-success-400">
                        {mol.predicted_pIC50.toFixed(2)}
                      </td>
                      <td className="py-2.5 px-3 text-right font-mono font-bold text-primary-300">
                        {mol.bioactivity_score.toFixed(1)} / 100
                      </td>
                      <td className="py-2.5 px-3 text-right font-mono text-slate-400">{mol.molecular_weight.toFixed(1)}</td>
                      <td className="py-2.5 px-3 text-right font-mono text-slate-400">{mol.logP.toFixed(2)}</td>
                      <td className="py-2.5 px-3 text-center">
                        {mol.lipinski_pass ? (
                          <span className="px-2 py-0.5 rounded-full bg-success-500/15 text-success-400 text-[10px] font-bold">
                            PASS
                          </span>
                        ) : (
                          <span className="px-2 py-0.5 rounded-full bg-red-500/15 text-red-400 text-[10px] font-bold">
                            FAIL
                          </span>
                        )}
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={9} className="py-8 text-center text-slate-500">
                      No candidate molecules match your filter criteria.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          <div className="flex items-center justify-between pt-3 border-t border-white/5 text-xs text-slate-400">
            <div>
              Showing page {page} of {Math.ceil(totalCount / pageSize) || 1}
            </div>
            <div className="flex items-center gap-2">
              <Button
                size="sm"
                variant="ghost"
                disabled={page <= 1}
                onClick={() => setPage(page - 1)}
              >
                Previous
              </Button>
              <Button
                size="sm"
                variant="ghost"
                disabled={page * pageSize >= totalCount}
                onClick={() => setPage(page + 1)}
              >
                Next
              </Button>
            </div>
          </div>

        </div>

        {/* Scientific disclaimer */}
        <div className="glass-card p-4 border border-amber-500/20 text-slate-400 text-xs text-center space-y-1">
          <p className="font-semibold text-amber-400">⚠️ Scientific Disclaimer</p>
          <p>
            Predicted pIC50 and Bioactivity Scores are computational machine learning predictions trained on historical ChEMBL IC50 data.
            They prioritize candidates for further computational screening (QAOA / Molecular Docking) and do not constitute clinical validation or medical advice.
          </p>
        </div>

      </div>
    </div>
  );
};
