/**
 * Shared TypeScript types for the Hybrid Quantum-AI Drug Discovery Platform.
 */

// ── Authentication ────────────────────────────────────────────

export interface User {
  id: number;
  email: string;
  username: string;
  full_name: string | null;
  is_active: boolean;
  is_superuser: boolean;
  created_at: string;
}

export interface AuthToken {
  access_token: string;
  token_type: string;
  expires_in: number;
  user: User;
}

// ── Experiment ────────────────────────────────────────────────

export type ExperimentStatus = 'PENDING' | 'RUNNING' | 'COMPLETED' | 'FAILED';
export type JobStatus = 'PENDING' | 'RUNNING' | 'COMPLETED' | 'FAILED';

export interface Experiment {
  id: number;
  name: string;
  description: string | null;
  status: ExperimentStatus;
  owner_id: number;
  target_id: number | null;
  dataset_path: string | null;
  raw_record_count: number | null;
  processed_record_count: number | null;
  preprocess_status: JobStatus;
  screen_status: JobStatus;
  quantum_status: JobStatus;
  docking_status: JobStatus;
  config: Record<string, unknown> | null;
  preprocessing_report: PreprocessingReport | null;
  created_at: string;
  updated_at: string;
  completed_at: string | null;
}

export interface PreprocessingReport {
  initial_records: number;
  valid_records: number;
  removed_records: number;
  duplicate_records: number;
  missing_smiles: number;
  final_records: number;
  unique_molecules: number;
}

// ── Target ────────────────────────────────────────────────────

export interface Target {
  id: number;
  name: string;
  chembl_id: string | null;
  uniprot_id: string | null;
  organism: string | null;
  target_type: string | null;
  description: string | null;
  pdb_id: string | null;
}

// ── Molecule ──────────────────────────────────────────────────

export type BioactivityClass = 'active' | 'inactive' | 'intermediate';

export interface Molecule {
  id: number;
  experiment_id: number;
  chembl_id: string | null;
  smiles: string | null;
  standard_value: number | null;
  standard_units: string | null;
  pic50: number | null;
  bioactivity_class: BioactivityClass | null;
  molecular_weight: number | null;
  logp: number | null;
  tpsa: number | null;
  hbd: number | null;
  hba: number | null;
  rotatable_bonds: number | null;
  ring_count: number | null;
  fraction_csp3: number | null;
  lipinski_pass: boolean | null;
}

// ── AI Prediction ─────────────────────────────────────────────

export interface Prediction {
  id: number;
  experiment_id: number;
  molecule_id: number;
  predicted_pic50: number | null;
  bioactivity_score: number | null;
  confidence: number | null;
  is_active_predicted: boolean | null;
}

// ── Model Version ─────────────────────────────────────────────

export interface ModelVersion {
  id: number;
  model_name: string;
  version: string;
  training_date: string;
  is_active: boolean;
  mae: number | null;
  rmse: number | null;
  r2: number | null;
  n_train: number | null;
  n_test: number | null;
  features_used: string[] | null;
  hyperparameters: Record<string, unknown> | null;
}

// ── Quantum Optimization ──────────────────────────────────────

export interface QuantumOptimization {
  id: number;
  experiment_id: number;
  status: JobStatus;
  n_candidates_input: number | null;
  n_candidates_selected: number | null;
  qaoa_depth: number | null;
  backend_type: string | null;
  backend_name: string | null;
  classical_objective_value: number | null;
  qaoa_objective_value: number | null;
  classical_runtime_seconds: number | null;
  qaoa_runtime_seconds: number | null;
}

// ── Docking ───────────────────────────────────────────────────

export interface DockingResult {
  id: number;
  molecule_id: number;
  binding_affinity: number | null;
  best_pose_rmsd_lb: number | null;
  n_poses_returned: number | null;
}

// ── Final Ranking ─────────────────────────────────────────────

export interface FinalRanking {
  id: number;
  experiment_id: number;
  molecule_id: number;
  rank: number | null;
  bioactivity_score_norm: number | null;
  drug_likeness_score_norm: number | null;
  quantum_score_norm: number | null;
  docking_score_norm: number | null;
  final_score: number | null;
  weights_used: Record<string, number> | null;
  methodology_notes: string | null;
}

// ── API Response Wrappers ─────────────────────────────────────

export interface ApiError {
  error: string;
  message: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

// ── Health Check ─────────────────────────────────────────────

export interface HealthResponse {
  status: 'ok' | 'degraded';
  app_name: string;
  version: string;
  timestamp: string;
  database: {
    connected: boolean;
    url_type: string;
  };
}

// ── Pipeline Steps ────────────────────────────────────────────

export interface PipelineStep {
  id: string;
  label: string;
  description: string;
  icon: string;
  status: JobStatus | 'not_started';
}

// ── Dashboard Stats ───────────────────────────────────────────

export interface DashboardStats {
  total_experiments: number;
  active_experiments: number;
  completed_experiments: number;
  failed_experiments: number;
  total_targets: number;
  total_molecules: number;
  total_predictions: number;
  total_docking_runs: number;
}

// ── Enriched Experiment (with nested target) ──────────────────

export interface ExperimentWithTarget extends Experiment {
  target: Target | null;
  dataset_version: string | null;
}

export interface ExperimentListItem {
  id: number;
  name: string;
  description: string | null;
  status: ExperimentStatus;
  target: Target | null;
  dataset_path: string | null;
  raw_record_count: number | null;
  processed_record_count: number | null;
  created_at: string;
  updated_at: string | null;
}

// ── Pipeline & ML Types ───────────────────────────────────────

export interface PreprocessingReportData {
  initial_records: number;
  final_records: number;
  unique_molecules: number;
  total_removed: number;
  removed: Record<string, number>;
  pic50_stats: {
    min: number;
    max: number;
    mean: number;
    median: number;
    std: number;
  };
  settings: Record<string, unknown>;
}

export interface ModelPerformanceMetrics {
  MAE: number | null;
  RMSE: number | null;
  R2: number | null;
  n_test_samples: number | null;
}

export interface ModelDetail {
  hyperparameters: Record<string, unknown>;
  model_file: string | null;
  test_metrics: ModelPerformanceMetrics;
  training_time_seconds: number | null;
}

export interface ModelComparisonResponse {
  metadata: {
    training_date: string;
    dataset: string;
    dataset_source: string;
    target: string;
    target_chembl_id: string;
    chembl_version: string;
    random_seed: number;
    feature_type: string;
    features_used: string[];
    morgan_radius: number;
    morgan_nbits: number;
  };
  dataset_stats: {
    initial_records: number;
    final_molecules: number;
    valid_rdkit_molecules: number;
    invalid_rdkit_molecules: number;
    n_train: number;
    n_val: number;
    n_test: number;
  };
  models: {
    RandomForest: ModelDetail;
    XGBoost: ModelDetail;
  };
  best_model_by_r2: string;
}

export interface MoleculePredictionItem {
  molecule_chembl_id: string;
  smiles: string;
  IC50_nM: number;
  pIC50: number;
  predicted_pIC50: number;
  bioactivity_score: number;
  molecular_weight: number;
  logP: number;
  TPSA: number;
  HBD: number;
  HBA: number;
  rotatable_bonds: number;
  ring_count: number;
  fraction_csp3: number;
  lipinski_pass: boolean;
}

export interface PredictionListResponse {
  total_molecules: number;
  model_used: string;
  predictions: MoleculePredictionItem[];
}
