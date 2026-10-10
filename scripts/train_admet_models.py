"""
ADMET Model Training Script — Milestone 4.

Trains two SEPARATE models on SEPARATE datasets:
  1. Toxicity Classifier (Tox21, NR-AR endpoint) — Random Forest Classifier
  2. Solubility Regressor (Delaney ESOL)         — Random Forest Regressor

These are INDEPENDENT of the EGFR pIC50 bioactivity model.
The EGFR dataset (data/raw/EGFR_bioactivity_raw.csv) is NOT used here.

Usage:
  python scripts/train_admet_models.py

Output:
  models/tox21_nrar_classifier.joblib
  models/tox21_nrar_scaler.joblib
  models/tox21_training_results.json
  models/esol_solubility_regressor.joblib
  models/esol_solubility_scaler.joblib
  models/esol_training_results.json
"""
import sys
import time
import logging
from pathlib import Path

# Ensure project root is on path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    encoding="utf-8",
)
logger = logging.getLogger(__name__)

from ml.admet.config import (
    TOX21_PATH, TOX21_TARGET_ENDPOINT,
    TOX_MODEL_PATH, TOX_SCALER_PATH, TOX_RESULTS_PATH,
    ESOL_PATH, SOL_MODEL_PATH, SOL_SCALER_PATH, SOL_RESULTS_PATH,
    RANDOM_SEED,
)
from ml.admet.toxicity.pipeline import train_toxicity_model
from ml.admet.solubility.pipeline import train_solubility_model


def main():
    print()
    print("=" * 60)
    print("ADMET Model Training Pipeline — Milestone 4")
    print("=" * 60)
    print()
    print("These models are SEPARATE from the EGFR pIC50 model.")
    print("They use separate datasets and separate training pipelines.")
    print()

    # ── 1. Toxicity Model ──────────────────────────────────────
    print("[1/2] Training Toxicity Classifier (Tox21 NR-AR endpoint)...")
    print(f"  Dataset: {TOX21_PATH}")
    print(f"  Endpoint: {TOX21_TARGET_ENDPOINT} (Nuclear Receptor - Androgen Receptor)")
    print("  Labels: Binary (0=inactive, 1=active/toxic)")
    print("  Class imbalance: ~309 toxic / ~6956 non-toxic -> class_weight=balanced")

    t0 = time.time()
    tox_results = train_toxicity_model(
        tox21_path=TOX21_PATH,
        endpoint=TOX21_TARGET_ENDPOINT,
        model_path=TOX_MODEL_PATH,
        scaler_path=TOX_SCALER_PATH,
        results_path=TOX_RESULTS_PATH,
        random_seed=RANDOM_SEED,
    )
    tox_time = time.time() - t0

    m = tox_results["metrics"]
    print(f"  Training time: {tox_time:.1f}s")
    print(f"  Test samples: {m['n_test_samples']}")
    print(f"  Accuracy:  {m['accuracy']:.4f}")
    print(f"  Precision: {m['precision']:.4f}")
    print(f"  Recall:    {m['recall']:.4f}")
    print(f"  F1:        {m['F1']:.4f}")
    print(f"  ROC-AUC:   {m['ROC_AUC']:.4f}  <- primary metric")
    print(f"  Saved: {TOX_MODEL_PATH.name}")
    print()

    # ── 2. Solubility Model ────────────────────────────────────
    print("[2/2] Training Solubility Regressor (Delaney ESOL)...")
    print(f"  Dataset: {ESOL_PATH}")
    print("  Target: measured log solubility (log10 mol/L)")
    print("  Model: Random Forest Regressor")

    t0 = time.time()
    sol_results = train_solubility_model(
        esol_path=ESOL_PATH,
        model_path=SOL_MODEL_PATH,
        scaler_path=SOL_SCALER_PATH,
        results_path=SOL_RESULTS_PATH,
        random_seed=RANDOM_SEED,
    )
    sol_time = time.time() - t0

    m = sol_results["metrics"]
    print(f"  Training time: {sol_time:.1f}s")
    print(f"  Test samples: {m['n_test_samples']}")
    print(f"  MAE:  {m['MAE']:.4f}")
    print(f"  RMSE: {m['RMSE']:.4f}")
    print(f"  R2:   {m['R2']:.4f}")
    print(f"  Saved: {SOL_MODEL_PATH.name}")
    print()

    # ── Summary ────────────────────────────────────────────────
    print("=" * 60)
    print("ADMET TRAINING COMPLETE")
    print("=" * 60)
    print()
    print("Generated files:")
    for p in [TOX_MODEL_PATH, TOX_SCALER_PATH, TOX_RESULTS_PATH,
               SOL_MODEL_PATH, SOL_SCALER_PATH, SOL_RESULTS_PATH]:
        print(f"  {p}")

    return {"toxicity": tox_results, "solubility": sol_results}


if __name__ == "__main__":
    results = main()
