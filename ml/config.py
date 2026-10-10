"""
ML Configuration for Hybrid Quantum-AI Drug Discovery Platform.

All hyperparameters, feature settings, and dataset paths are centralised here.
Never hardcode these values in other modules.

Reproducibility:
  Python: 3.13
  scikit-learn: 1.9.0
  xgboost: 3.2.0
  rdkit: 2026.3.5
"""
import os
from pathlib import Path

# ── Project root detection ─────────────────────────────────────
# This file lives at <project_root>/ml/config.py
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# ── Dataset paths ──────────────────────────────────────────────
RAW_DATA_DIR   = PROJECT_ROOT / "data" / "raw"
PROCESSED_DATA_DIR = PROJECT_ROOT / "data" / "processed"
MODELS_DIR     = PROJECT_ROOT / "models"

RAW_DATASET_FILENAME = "EGFR_bioactivity_raw.csv"
RAW_DATASET_PATH = RAW_DATA_DIR / RAW_DATASET_FILENAME

PROCESSED_DATASET_FILENAME = "EGFR_ML_dataset.csv"
PROCESSED_DATASET_PATH = PROCESSED_DATA_DIR / PROCESSED_DATASET_FILENAME

FINGERPRINT_MATRIX_FILENAME = "EGFR_fingerprints.npy"
FINGERPRINT_IDS_FILENAME    = "EGFR_fingerprint_ids.txt"
PREPROCESSING_REPORT_FILENAME = "EGFR_preprocessing_report.json"
SPLIT_INFO_FILENAME = "EGFR_split_info.json"

# ── Dataset provenance ─────────────────────────────────────────
DATASET_SOURCE = "ChEMBL Database"
DATASET_TARGET = "Epidermal Growth Factor Receptor"
DATASET_TARGET_CHEMBL_ID = "CHEMBL203"
DATASET_TARGET_UNIPROT   = "P00533"
DATASET_CHEMBL_VERSION   = "chembl_33"

# ── Required raw dataset columns ──────────────────────────────
REQUIRED_RAW_COLUMNS = [
    "molecule_chembl_id",
    "canonical_smiles",
    "standard_type",
    "standard_value",
    "standard_units",
]

# ── Preprocessing rules ────────────────────────────────────────
ALLOWED_STANDARD_TYPE  = "IC50"
ALLOWED_STANDARD_UNITS = "nM"

# Optionally exclude rows with known data quality issues
EXCLUDE_DATA_VALIDITY_ERRORS = True

# pIC50 formula: pIC50 = 9 - log10(IC50_nM)
# Equivalent to pIC50 = -log10(IC50_M)  [since 1 nM = 1e-9 M]
PIC50_FORMULA_BASE = 9  # 9 = -log10(1e-9)

# Molecule deduplication strategy
# 'median' — take median pIC50 per molecule (reduces outlier bias)
# 'min'    — take minimum IC50 per molecule (most potent measurement)
DEDUPLICATION_STRATEGY = "median"

# pIC50 valid range filter (remove extreme outliers)
PIC50_MIN = 3.0   # IC50 = 1 mM upper bound
PIC50_MAX = 12.0  # IC50 < 1 pM lower bound (extremely rare)

# ── RDKit Feature Configuration ───────────────────────────────
# Morgan fingerprint settings (documented for reproducibility)
MORGAN_RADIUS = 2      # Equivalent to ECFP4
MORGAN_NBITS  = 2048   # Number of bits

# Descriptor column names (in order)
DESCRIPTOR_COLUMNS = [
    "molecular_weight",
    "logP",
    "TPSA",
    "HBD",
    "HBA",
    "rotatable_bonds",
    "ring_count",
    "fraction_csp3",
]

# Lipinski Rule of Five thresholds
LIPINSKI_MW_MAX   = 500.0
LIPINSKI_LOGP_MAX = 5.0
LIPINSKI_HBD_MAX  = 5
LIPINSKI_HBA_MAX  = 10

# ── Train/Val/Test Split ──────────────────────────────────────
RANDOM_SEED  = 42    # Seed for ALL random operations
TRAIN_RATIO  = 0.70  # 70% training
VAL_RATIO    = 0.15  # 15% validation
TEST_RATIO   = 0.15  # 15% test  (must sum to 1.0)

# ── Random Forest Hyperparameters ────────────────────────────
RF_HYPERPARAMS = {
    "n_estimators": 200,
    "max_depth": None,          # Unlimited depth
    "min_samples_split": 2,
    "min_samples_leaf": 1,
    "max_features": "sqrt",
    "random_state": RANDOM_SEED,
    "n_jobs": -1,               # Use all CPU cores
}

# ── XGBoost Hyperparameters ──────────────────────────────────
XGB_HYPERPARAMS = {
    "n_estimators": 200,
    "learning_rate": 0.1,
    "max_depth": 6,
    "subsample": 0.8,
    "colsample_bytree": 0.8,
    "random_state": RANDOM_SEED,
    "n_jobs": -1,
    "verbosity": 0,
}

# ── Model artifact names ──────────────────────────────────────
RF_MODEL_FILENAME  = "egfr_random_forest.joblib"
XGB_MODEL_FILENAME = "egfr_xgboost.joblib"
SCALER_FILENAME    = "egfr_descriptor_scaler.joblib"
TRAINING_RESULTS_FILENAME = "training_results.json"

RF_MODEL_PATH  = MODELS_DIR / RF_MODEL_FILENAME
XGB_MODEL_PATH = MODELS_DIR / XGB_MODEL_FILENAME
SCALER_PATH    = MODELS_DIR / SCALER_FILENAME
TRAINING_RESULTS_PATH = MODELS_DIR / TRAINING_RESULTS_FILENAME
