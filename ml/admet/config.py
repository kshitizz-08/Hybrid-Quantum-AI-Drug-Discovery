"""
ADMET Configuration for Hybrid Quantum-AI Drug Discovery Platform.

All dataset paths, model hyperparameters, score weights, and filtering
thresholds are centralised here for reproducibility and transparency.
"""
from pathlib import Path

# ── Project root ───────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

RAW_DATA_DIR       = PROJECT_ROOT / "data" / "raw"
PROCESSED_DATA_DIR = PROJECT_ROOT / "data" / "processed"
MODELS_DIR         = PROJECT_ROOT / "models"

# ── Tox21 Toxicity Dataset ─────────────────────────────────────
TOX21_FILENAME = "Tox21.csv"
TOX21_PATH     = RAW_DATA_DIR / TOX21_FILENAME

# Source documentation
TOX21_SOURCE = "MoleculeNet / Tox21 Challenge Dataset"
TOX21_URL    = "https://deepchemdata.s3-us-west-1.amazonaws.com/datasets/tox21.csv.gz"

# Chosen endpoint: NR-AR (Nuclear Receptor — Androgen Receptor)
# Rationale: Well-validated, relevant to drug selectivity, suitable for EGFR drug screening
# Labels: 0 = inactive (non-toxic), 1 = active (toxic/problematic)
TOX21_TARGET_ENDPOINT = "NR-AR"
TOX21_SMILES_COL      = "smiles"
TOX21_MOL_ID_COL      = "mol_id"
TOX21_ALL_ENDPOINTS   = [
    "NR-AR", "NR-AR-LBD", "NR-AhR", "NR-Aromatase",
    "NR-ER", "NR-ER-LBD", "NR-PPAR-gamma",
    "SR-ARE", "SR-ATAD5", "SR-HSE", "SR-MMP", "SR-p53",
]

# Toxicity model
TOX_MODEL_FILENAME  = "tox21_nrar_classifier.joblib"
TOX_SCALER_FILENAME = "tox21_nrar_scaler.joblib"
TOX_RESULTS_FILENAME = "tox21_training_results.json"
TOX_MODEL_PATH  = MODELS_DIR / TOX_MODEL_FILENAME
TOX_SCALER_PATH = MODELS_DIR / TOX_SCALER_FILENAME
TOX_RESULTS_PATH = MODELS_DIR / TOX_RESULTS_FILENAME

# Toxicity model hyperparameters
RANDOM_SEED = 42
TOX_RF_HYPERPARAMS = {
    "n_estimators": 200,
    "max_depth": None,
    "class_weight": "balanced",    # handles class imbalance (309 toxic vs 6956 non-toxic)
    "random_state": RANDOM_SEED,
    "n_jobs": -1,
}
TOX_TRAIN_RATIO = 0.70
TOX_TEST_RATIO  = 0.30

# ── Delaney ESOL Solubility Dataset ────────────────────────────
ESOL_FILENAME = "delaney-processed.csv"
ESOL_PATH     = RAW_DATA_DIR / ESOL_FILENAME

# Source documentation
ESOL_SOURCE  = "Delaney (2004) — Molecular Informatics"
ESOL_CITATION = "Delaney, J.S. (2004). ESOL: Estimating Aqueous Solubility Directly from Molecular Structure. J. Chem. Inf. Comput. Sci., 44(3), 1000-1005."

ESOL_SMILES_COL  = "smiles"
ESOL_TARGET_COL  = "measured log solubility in mols per litre"  # log10 mol/L

# Solubility model
SOL_MODEL_FILENAME   = "esol_solubility_regressor.joblib"
SOL_SCALER_FILENAME  = "esol_solubility_scaler.joblib"
SOL_RESULTS_FILENAME = "esol_training_results.json"
SOL_MODEL_PATH   = MODELS_DIR / SOL_MODEL_FILENAME
SOL_SCALER_PATH  = MODELS_DIR / SOL_SCALER_FILENAME
SOL_RESULTS_PATH = MODELS_DIR / SOL_RESULTS_FILENAME

SOL_RF_HYPERPARAMS = {
    "n_estimators": 200,
    "max_depth": None,
    "random_state": RANDOM_SEED,
    "n_jobs": -1,
}
SOL_TRAIN_RATIO = 0.70
SOL_TEST_RATIO  = 0.30

# ── Candidate Scoring Formula ──────────────────────────────────
#
# composite_score = (
#     bioactivity_weight * bioactivity_score_norm
#   + solubility_weight  * solubility_score_norm
#   + drug_likeness_weight * drug_likeness_score_norm
#   - toxicity_weight   * toxicity_risk_norm
# )
#
# All component scores are normalized to [0, 1].
# Final composite_score is in [0, 1].

SCORE_WEIGHTS = {
    "bioactivity_weight":   0.40,
    "toxicity_weight":      0.30,
    "solubility_weight":    0.20,
    "drug_likeness_weight": 0.10,
}

# pIC50 normalization range (based on EGFR dataset observed range)
PIC50_NORM_MIN = 4.0
PIC50_NORM_MAX = 11.0

# Solubility normalization: log solubility range
# Good solubility: > -4, Poor: < -6
SOL_NORM_MIN = -10.0
SOL_NORM_MAX =   2.0

# Toxicity: probability threshold for "high risk"
TOX_HIGH_RISK_THRESHOLD = 0.5

# ── Candidate Filtering Defaults ──────────────────────────────
DEFAULT_CANDIDATE_COUNT  = 50    # Start from top-N by pIC50 before ADMET
DEFAULT_QUANTUM_N        = 20    # Candidates entering QUBO
DEFAULT_QUANTUM_K        = 5     # Number to select via QAOA
DEFAULT_MIN_PIC50        = 7.0   # Minimum predicted pIC50
DEFAULT_MAX_TOX_RISK     = 0.5   # Maximum toxicity probability
DEFAULT_MIN_LOG_SOL      = -6.0  # Minimum log solubility (mol/L)
DEFAULT_REQUIRE_LIPINSKI = False  # Lipinski pass not required by default

# ── ADMET results filenames ───────────────────────────────────
ADMET_RESULTS_FILENAME = "EGFR_admet_results.csv"
ADMET_RESULTS_PATH = PROCESSED_DATA_DIR / ADMET_RESULTS_FILENAME
