/**
 * ModelManagementPage - Full model registry and performance dashboard.
 *
 * Displays all 4 trained models with real metrics from training_results.json:
 *   1. EGFR RandomForest (pIC50 regression)
 *   2. EGFR XGBoost     (pIC50 regression)
 *   3. Tox21 NR-AR Classifier (toxicity binary)
 *   4. ESOL Solubility Regressor (log solubility)
 */
import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';

// ── Real model data from training_results.json ────────────────
const MODELS = [
  {
    id: 'egfr-rf',
    name: 'EGFR RandomForest',
    type: 'regression',
    task: 'pIC50 Prediction',
    target: 'EGFR / CHEMBL203',
    dataset: 'ChEMBL v33',
    file: 'egfr_random_forest.joblib',
    fileSizeMB: 115.2,
    trainedAt: '2026-08-17',
    isBest: true,
    status: 'active',
    color: 'violet',
    icon: '🌲',
    hyperparams: {
      n_estimators: 200,
      max_depth: 'None (unlimited)',
      max_features: 'sqrt',
      min_samples_split: 2,
      min_samples_leaf: 1,
      random_state: 42,
    },
    metrics: {
      MAE: 0.7339,
      RMSE: 0.9574,
      R2: 0.4775,
    },
    dataset_stats: {
      'Initial Records': '18,454',
      'Final Molecules': '10,407',
      'Train / Val / Test': '7,284 / 1,561 / 1,562',
      'Training Time': '0.48s',
    },
    features: ['molecular_weight', 'logP', 'TPSA', 'HBD', 'HBA', 'rotatable_bonds', 'ring_count', 'fraction_csp3'],
    description: 'RandomForest regressor predicting pIC50 bioactivity for EGFR-targeting compounds. Uses RDKit physicochemical descriptors. Best R² on the test set.',
  },
  {
    id: 'egfr-xgb',
    name: 'EGFR XGBoost',
    type: 'regression',
    task: 'pIC50 Prediction',
    target: 'EGFR / CHEMBL203',
    dataset: 'ChEMBL v33',
    file: 'egfr_xgboost.joblib',
    fileSizeMB: 0.83,
    trainedAt: '2026-08-17',
    isBest: false,
    status: 'active',
    color: 'cyan',
    icon: '⚡',
    hyperparams: {
      n_estimators: 200,
      learning_rate: 0.1,
      max_depth: 6,
      subsample: 0.8,
      colsample_bytree: 0.8,
      random_state: 42,
    },
    metrics: {
      MAE: 0.7703,
      RMSE: 0.9979,
      R2: 0.4324,
    },
    dataset_stats: {
      'Initial Records': '18,454',
      'Final Molecules': '10,407',
      'Train / Val / Test': '7,284 / 1,561 / 1,562',
      'Training Time': '0.31s',
    },
    features: ['molecular_weight', 'logP', 'TPSA', 'HBD', 'HBA', 'rotatable_bonds', 'ring_count', 'fraction_csp3'],
    description: 'Gradient-boosted trees for EGFR pIC50 regression. Faster training than RandomForest with competitive performance.',
  },
  {
    id: 'tox21-nrar',
    name: 'Tox21 Classifier',
    type: 'classification',
    task: 'Toxicity Prediction',
    target: 'Nuclear Receptor — Androgen Receptor (NR-AR)',
    dataset: 'Tox21 — MoleculeNet',
    file: 'tox21_nrar_classifier.joblib',
    fileSizeMB: 10.9,
    trainedAt: '2026-08-17',
    isBest: false,
    status: 'active',
    color: 'red',
    icon: '🧬',
    hyperparams: {
      n_estimators: 200,
      max_depth: 'None',
      class_weight: 'balanced',
      random_state: 42,
    },
    metrics: {
      accuracy: 0.9665,
      precision: 0.6610,
      recall: 0.4239,
      F1: 0.5166,
      ROC_AUC: 0.7815,
    },
    dataset_stats: {
      'Total Rows': '7,831',
      'Toxic (NR-AR=1)': '309',
      'Non-toxic (NR-AR=0)': '6,956',
      'Train / Test': '5,080 / 2,178',
    },
    features: ['8 RDKit descriptors', '2048 Morgan fingerprints (ECFP4, r=2)'],
    description: 'Binary classifier for NR-AR toxicity endpoint. Trained on Tox21 with class balancing. High accuracy due to class imbalance; ROC-AUC is primary metric.',
  },
  {
    id: 'esol-sol',
    name: 'ESOL Solubility',
    type: 'regression',
    task: 'Aqueous Solubility',
    target: 'Log Solubility (mol/L)',
    dataset: 'Delaney ESOL (2004)',
    file: 'esol_solubility_regressor.joblib',
    fileSizeMB: 12.5,
    trainedAt: '2026-08-17',
    isBest: false,
    status: 'active',
    color: 'teal',
    icon: '💧',
    hyperparams: {
      n_estimators: 200,
      max_depth: 'None',
      random_state: 42,
    },
    metrics: {
      MAE: 0.5116,
      RMSE: 0.7305,
      R2: 0.8830,
    },
    dataset_stats: {
      'Total Molecules': '1,128',
      'Train / Test': '789 / 339',
      'Target Range': '-11.6 to +1.58 log mol/L',
      'Mean Target': '-3.05 log mol/L',
    },
    features: ['molecular_weight', 'logP', 'TPSA', 'HBD', 'HBA', 'rotatable_bonds', 'ring_count', 'fraction_csp3'],
    description: 'Predicts aqueous solubility (ESOL) using the Delaney dataset. Highest R² among all models (0.883). Used in ADMET pipeline for drug-likeness scoring.',
  },
];

// ── Color maps ────────────────────────────────────────────────
const COLOR_MAP: Record<string, { bg: string; border: string; text: string; badge: string }> = {
  violet: { bg: 'bg-violet-500/10', border: 'border-violet-500/30', text: 'text-violet-400', badge: 'bg-violet-500/20 text-violet-300 border-violet-500/30' },
  cyan:   { bg: 'bg-cyan-500/10',   border: 'border-cyan-500/30',   text: 'text-cyan-400',   badge: 'bg-cyan-500/20   text-cyan-300   border-cyan-500/30'   },
  red:    { bg: 'bg-red-500/10',    border: 'border-red-500/30',    text: 'text-red-400',    badge: 'bg-red-500/20    text-red-300    border-red-500/30'    },
  teal:   { bg: 'bg-teal-500/10',   border: 'border-teal-500/30',   text: 'text-teal-400',  badge: 'bg-teal-500/20   text-teal-300   border-teal-500/30'   },
};

// ── Metric bar ────────────────────────────────────────────────
const MetricBar: React.FC<{ label: string; value: number; max?: number; good?: 'high' | 'low'; color: string }> = ({
  label, value, max = 1, good = 'high', color,
}) => {
  const pct = Math.min(Math.round((value / max) * 100), 100);
  return (
    <div className="space-y-1">
      <div className="flex justify-between items-center">
        <span className="text-slate-500 text-xs">{label}</span>
        <span className={`text-xs font-mono font-bold ${color}`}>{value.toFixed(4)}</span>
      </div>
      <div className="h-1.5 bg-surface-700 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-700 ${
            good === 'high' ? (pct > 70 ? 'bg-emerald-500' : pct > 40 ? 'bg-amber-500' : 'bg-red-500') :
                              (pct < 30 ? 'bg-emerald-500' : pct < 60 ? 'bg-amber-500' : 'bg-red-500')
          }`}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
};

// ── Model card ────────────────────────────────────────────────
const ModelCard: React.FC<{ model: typeof MODELS[0]; isExpanded: boolean; onToggle: () => void }> = ({
  model, isExpanded, onToggle,
}) => {
  const c = COLOR_MAP[model.color];
  const isRegression = model.type === 'regression';

  return (
    <div className={`glass-card overflow-hidden border ${isExpanded ? c.border : 'border-white/5'} transition-all duration-300`}>
      {/* Card header */}
      <button
        id={`model-card-${model.id}`}
        onClick={onToggle}
        className="w-full flex items-start gap-4 p-5 text-left hover:bg-white/[0.02] transition-colors"
      >
        <div className={`w-11 h-11 rounded-xl flex items-center justify-center text-xl flex-shrink-0 ${c.bg} border ${c.border}`}>
          {model.icon}
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <h3 className="text-white font-bold text-sm">{model.name}</h3>
            {model.isBest && (
              <span className="text-[9px] font-bold px-2 py-0.5 rounded-full bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">
                BEST R²
              </span>
            )}
            <span className={`text-[9px] font-bold px-2 py-0.5 rounded-full border ${c.badge}`}>
              {model.type === 'regression' ? 'REGRESSION' : 'CLASSIFIER'}
            </span>
            <span className="text-[9px] font-bold px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
              ● ACTIVE
            </span>
          </div>
          <p className="text-slate-500 text-xs mt-0.5">{model.task} · {model.target}</p>
          <p className="text-slate-600 text-[11px] mt-1 line-clamp-1">{model.description}</p>
        </div>
        <div className="flex items-center gap-6 flex-shrink-0 ml-2">
          {isRegression ? (
            <>
              <div className="text-center hidden sm:block">
                <p className="text-[10px] text-slate-500">R²</p>
                <p className={`text-sm font-bold font-mono ${c.text}`}>
                  {(model.metrics as { R2: number }).R2.toFixed(3)}
                </p>
              </div>
              <div className="text-center hidden sm:block">
                <p className="text-[10px] text-slate-500">MAE</p>
                <p className="text-sm font-bold font-mono text-slate-300">
                  {(model.metrics as { MAE: number }).MAE.toFixed(3)}
                </p>
              </div>
            </>
          ) : (
            <>
              <div className="text-center hidden sm:block">
                <p className="text-[10px] text-slate-500">ROC-AUC</p>
                <p className={`text-sm font-bold font-mono ${c.text}`}>
                  {(model.metrics as { ROC_AUC: number }).ROC_AUC.toFixed(3)}
                </p>
              </div>
              <div className="text-center hidden sm:block">
                <p className="text-[10px] text-slate-500">F1</p>
                <p className="text-sm font-bold font-mono text-slate-300">
                  {(model.metrics as { F1: number }).F1.toFixed(3)}
                </p>
              </div>
            </>
          )}
          <svg className={`w-4 h-4 text-slate-500 transition-transform duration-300 flex-shrink-0 ${isExpanded ? 'rotate-180' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </div>
      </button>

      {/* Expanded detail */}
      {isExpanded && (
        <div className="border-t border-white/5 p-5 space-y-6 animate-fade-in">
          <p className="text-slate-400 text-xs leading-relaxed">{model.description}</p>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
            {/* Performance Metrics */}
            <div className="space-y-3">
              <h4 className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">Performance Metrics</h4>
              {isRegression ? (
                <>
                  <MetricBar label="R² Score" value={(model.metrics as { R2: number }).R2} good="high" color={c.text} />
                  <MetricBar label="MAE" value={(model.metrics as { MAE: number }).MAE} max={2} good="low" color={c.text} />
                  <MetricBar label="RMSE" value={(model.metrics as { RMSE: number }).RMSE} max={2} good="low" color={c.text} />
                </>
              ) : (
                <>
                  <MetricBar label="ROC-AUC" value={(model.metrics as { ROC_AUC: number }).ROC_AUC} good="high" color={c.text} />
                  <MetricBar label="F1 Score" value={(model.metrics as { F1: number }).F1} good="high" color={c.text} />
                  <MetricBar label="Precision" value={(model.metrics as { precision: number }).precision} good="high" color={c.text} />
                  <MetricBar label="Recall" value={(model.metrics as { recall: number }).recall} good="high" color={c.text} />
                  <MetricBar label="Accuracy" value={(model.metrics as { accuracy: number }).accuracy} good="high" color={c.text} />
                </>
              )}
            </div>

            {/* Dataset Stats */}
            <div className="space-y-3">
              <h4 className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">Dataset Statistics</h4>
              <div className="space-y-0">
                {Object.entries(model.dataset_stats).map(([k, v]) => (
                  <div key={k} className="flex justify-between py-1.5 border-b border-white/5 last:border-0">
                    <span className="text-slate-500 text-xs">{k}</span>
                    <span className="text-slate-300 text-xs font-mono font-medium">{v}</span>
                  </div>
                ))}
                <div className="flex justify-between py-1.5 border-b border-white/5">
                  <span className="text-slate-500 text-xs">Model File</span>
                  <span className="text-slate-400 text-[10px] font-mono">{model.file}</span>
                </div>
                <div className="flex justify-between py-1.5">
                  <span className="text-slate-500 text-xs">File Size</span>
                  <span className="text-slate-300 text-xs font-mono">{model.fileSizeMB} MB</span>
                </div>
              </div>
            </div>

            {/* Hyperparameters */}
            <div className="space-y-3">
              <h4 className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">Hyperparameters</h4>
              <div className="space-y-0">
                {Object.entries(model.hyperparams).map(([k, v]) => (
                  <div key={k} className="flex justify-between py-1.5 border-b border-white/5 last:border-0">
                    <span className="text-slate-500 text-xs">{k}</span>
                    <span className="text-slate-300 text-xs font-mono">{String(v)}</span>
                  </div>
                ))}
              </div>
              <div className="mt-3">
                <p className="text-[10px] font-bold text-slate-500 uppercase tracking-wider mb-2">Input Features</p>
                <div className="flex flex-wrap gap-1">
                  {model.features.map((f) => (
                    <span key={f} className={`text-[9px] font-mono px-1.5 py-0.5 rounded border ${c.badge}`}>{f}</span>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

// ── Summary stat ──────────────────────────────────────────────
const StatBlock: React.FC<{ label: string; value: string; sub?: string; color: string }> = ({ label, value, sub, color }) => (
  <div className="glass-card p-4 space-y-1">
    <p className="text-slate-500 text-xs">{label}</p>
    <p className={`text-xl font-bold font-mono ${color}`}>{value}</p>
    {sub && <p className="text-slate-600 text-xs">{sub}</p>}
  </div>
);

// ═══════════════════════════════════════════════════════════════
// MAIN PAGE
// ═══════════════════════════════════════════════════════════════

export const ModelManagementPage: React.FC = () => {
  const navigate = useNavigate();
  const { user } = useAuthStore();
  const [expandedId, setExpandedId] = useState<string | null>('egfr-rf');
  const [filter, setFilter] = useState<'all' | 'regression' | 'classification'>('all');

  if (!user) { navigate('/login'); return null; }

  const filtered = MODELS.filter((m) =>
    filter === 'all' ? true : filter === 'regression' ? m.type === 'regression' : m.type === 'classification'
  );

  const toggleExpand = (id: string) => setExpandedId(prev => prev === id ? null : id);

  return (
    <div className="min-h-screen pt-16 pl-56">
      <div className="max-w-5xl mx-auto px-6 py-10 space-y-6">

        {/* Header */}
        <div className="mb-2">
          <div className="section-divider mb-3" />
          <h1 className="text-2xl font-bold text-white tracking-tight">Model Management</h1>
          <p className="text-slate-500 text-sm mt-1">
            Trained ML model registry with real performance metrics and hyperparameters.
          </p>
        </div>

        {/* Summary stats */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <StatBlock label="Active Models" value="4" sub="All loaded" color="text-violet-400" />
          <StatBlock label="Best EGFR R²" value="0.478" sub="RandomForest" color="text-emerald-400" />
          <StatBlock label="ESOL R²" value="0.883" sub="Solubility model" color="text-teal-400" />
          <StatBlock label="Tox ROC-AUC" value="0.781" sub="NR-AR classifier" color="text-red-400" />
        </div>

        {/* Filter tabs */}
        <div className="flex items-center gap-2">
          {(['all', 'regression', 'classification'] as const).map((f) => (
            <button
              key={f}
              id={`model-filter-${f}`}
              onClick={() => setFilter(f)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all duration-150 border capitalize ${
                filter === f
                  ? 'bg-violet-600/30 border-violet-500/60 text-violet-300'
                  : 'bg-surface-700/60 border-white/5 text-slate-400 hover:text-slate-300'
              }`}
            >
              {f === 'all' ? `All Models (${MODELS.length})` : f === 'regression' ? `Regression (${MODELS.filter(m => m.type === 'regression').length})` : `Classification (${MODELS.filter(m => m.type === 'classification').length})`}
            </button>
          ))}
        </div>

        {/* Model cards */}
        <div className="space-y-3">
          {filtered.map((model) => (
            <ModelCard
              key={model.id}
              model={model}
              isExpanded={expandedId === model.id}
              onToggle={() => toggleExpand(model.id)}
            />
          ))}
        </div>

        {/* Pipeline integration note */}
        <div className="glass-card p-5 border border-white/5">
          <h3 className="text-white text-sm font-semibold mb-3">Pipeline Integration</h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {[
              { step: '1. Data Preprocessing', model: '—', note: 'RDKit descriptor extraction + Morgan fingerprints' },
              { step: '2. EGFR pIC50 Prediction', model: 'RandomForest + XGBoost', note: 'Both run in parallel; best R² (RF) used for ranking' },
              { step: '3. Toxicity Screen (ADMET)', model: 'Tox21 NR-AR Classifier', note: 'Binary prediction; tox_probability used for filtering' },
              { step: '4. Solubility (ADMET)', model: 'ESOL Solubility Regressor', note: 'log solubility (mol/L); used in composite ADMET score' },
            ].map(({ step, model, note }) => (
              <div key={step} className="bg-surface-800/40 rounded-xl p-3 space-y-1">
                <p className="text-violet-400 text-[10px] font-bold uppercase tracking-wider">{step}</p>
                <p className="text-white text-xs font-medium">{model}</p>
                <p className="text-slate-500 text-[10px] leading-relaxed">{note}</p>
              </div>
            ))}
          </div>
        </div>

        {/* Disclaimer */}
        <div className="rounded-xl border border-amber-500/20 bg-amber-500/5 px-5 py-4 flex gap-3">
          <svg className="w-5 h-5 text-amber-400 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <div>
            <p className="text-amber-400 text-xs font-semibold uppercase tracking-wider mb-1">Model Performance Disclaimer</p>
            <p className="text-amber-200/60 text-xs leading-relaxed">
              All metrics are evaluated on held-out test sets using the stated dataset splits. Model predictions are computational
              estimates only and are not clinically validated. Reported R² values reflect performance on curated ChEMBL/Tox21/ESOL datasets
              and may not generalise to out-of-distribution compound libraries or novel scaffolds.
            </p>
          </div>
        </div>

      </div>
    </div>
  );
};

export default ModelManagementPage;
