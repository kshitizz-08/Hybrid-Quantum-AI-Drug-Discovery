"""
EGFR Drug Discovery — Model Training Script
============================================

Reproducible end-to-end training pipeline:
  1. Load and validate raw dataset
  2. Preprocess (filter, convert, pIC50)
  3. Extract RDKit features (descriptors + Morgan fingerprints)
  4. Molecule-level train/val/test split (no data leakage)
  5. Train Random Forest Regressor
  6. Train XGBoost Regressor
  7. Evaluate both models on held-out test set
  8. Save model artifacts
  9. Save training results to JSON
  10. Print full summary

Usage:
    python scripts/train_egfr_models.py

All metrics come from real evaluation on held-out data.
No metrics are hardcoded or fabricated.

Reproducibility:
    Random seed: 42 (configured in ml/config.py)
    scikit-learn: 1.9.0
    xgboost: 3.2.0
    rdkit: 2026.3.5
"""
import json
import logging
import sys
import time
from pathlib import Path
from datetime import datetime

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.preprocessing import StandardScaler
import joblib

# ── Project root on sys.path ──────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from ml.config import (
    RAW_DATASET_PATH,
    PROCESSED_DATA_DIR,
    MODELS_DIR,
    PROCESSED_DATASET_PATH,
    FINGERPRINT_MATRIX_FILENAME,
    FINGERPRINT_IDS_FILENAME,
    SPLIT_INFO_FILENAME,
    RF_MODEL_PATH,
    XGB_MODEL_PATH,
    SCALER_PATH,
    TRAINING_RESULTS_PATH,
    RF_HYPERPARAMS,
    XGB_HYPERPARAMS,
    MORGAN_RADIUS,
    MORGAN_NBITS,
    RANDOM_SEED,
    TRAIN_RATIO,
    VAL_RATIO,
    TEST_RATIO,
    DESCRIPTOR_COLUMNS,
    DATASET_SOURCE,
    DATASET_TARGET,
    DATASET_TARGET_CHEMBL_ID,
    DATASET_CHEMBL_VERSION,
)
from ml.preprocessing.pipeline import preprocess_egfr_dataset, save_preprocessing_report
from ml.preprocessing.inspect import inspect_dataset
from ml.features.rdkit_features import compute_features_for_dataframe, check_lipinski

try:
    import xgboost as xgb
    XGBOOST_AVAILABLE = True
except ImportError:
    XGBOOST_AVAILABLE = False

# ── Logging ───────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


def evaluate_model(model, X_test: np.ndarray, y_test: np.ndarray) -> dict:
    """Evaluate a model on the test set and return real metrics."""
    y_pred = model.predict(X_test)
    mae  = mean_absolute_error(y_test, y_pred)
    rmse = np.sqrt(mean_squared_error(y_test, y_pred))
    r2   = r2_score(y_test, y_pred)
    return {
        "MAE":  float(mae),
        "RMSE": float(rmse),
        "R2":   float(r2),
        "n_test_samples": int(len(y_test)),
    }


def main():
    start_time = time.time()
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)

    print("\n" + "=" * 60)
    print("EGFR Drug Discovery — ML Training Pipeline")
    print("=" * 60)

    # ── 1. Load raw dataset ───────────────────────────────────
    print("\n[1/9] Loading raw dataset...")
    if not RAW_DATASET_PATH.exists():
        logger.error("Raw dataset not found: %s", RAW_DATASET_PATH)
        sys.exit(1)

    df_raw = pd.read_csv(RAW_DATASET_PATH, low_memory=False)
    print(f"  Loaded: {len(df_raw):,} rows, {len(df_raw.columns)} columns")

    # Quick inspection
    inspection = inspect_dataset(df_raw)
    print(f"  Unique molecules (raw): {inspection['unique_molecules']:,}")
    print(f"  SMILES present: {inspection['smiles_present']:,}/{inspection['total_rows']:,}")

    # ── 2. Preprocess ─────────────────────────────────────────
    print("\n[2/9] Preprocessing (filter, standardize, pIC50)...")
    df_clean, prep_report = preprocess_egfr_dataset(df_raw)
    save_preprocessing_report(prep_report)

    print(f"  Initial records:    {prep_report['initial_records']:>8,}")
    print(f"  Non-IC50 removed:   {prep_report['removed'].get('non_ic50_type', 0):>8,}")
    print(f"  Non-nM removed:     {prep_report['removed'].get('non_nM_units', 0):>8,}")
    print(f"  Missing SMILES:     {prep_report['removed'].get('missing_smiles', 0):>8,}")
    print(f"  Validity errors:    {prep_report['removed'].get('data_validity_errors', 0):>8,}")
    print(f"  Duplicates merged:  {prep_report['removed'].get('duplicate_measurements', 0):>8,}")
    print(f"  pIC50 out of range: {prep_report['removed'].get('pic50_out_of_range', 0):>8,}")
    print(f"  Final molecules:    {prep_report['final_records']:>8,}")
    print(f"  pIC50 range: [{prep_report['pic50_stats']['min']:.2f}, {prep_report['pic50_stats']['max']:.2f}]")
    print(f"  pIC50 median: {prep_report['pic50_stats']['median']:.2f}")

    # ── 3. RDKit feature extraction ────────────────────────────
    print("\n[3/9] Extracting RDKit descriptors and Morgan fingerprints...")
    print(f"  Morgan: radius={MORGAN_RADIUS}, nBits={MORGAN_NBITS} (ECFP4 equivalent)")

    descriptor_df, fp_matrix, valid_ids, feat_stats = compute_features_for_dataframe(
        df_clean,
        smiles_col="smiles",
        id_col="molecule_chembl_id",
        morgan_radius=MORGAN_RADIUS,
        morgan_nbits=MORGAN_NBITS,
    )

    print(f"  Valid molecules:    {feat_stats['valid_molecules']:>8,}")
    print(f"  Invalid (RDKit):   {feat_stats['invalid_molecules']:>8,}")
    print(f"  Fingerprint matrix: {fp_matrix.shape}")

    # Add Lipinski pass/fail
    descriptor_df["lipinski_pass"] = descriptor_df.apply(
        lambda r: check_lipinski(r.to_dict()), axis=1
    )
    lipinski_pass = descriptor_df["lipinski_pass"].sum()
    print(f"  Lipinski pass:      {lipinski_pass:>8,} ({100*lipinski_pass/len(descriptor_df):.1f}%)")

    # ── 4. Build final ML dataset ─────────────────────────────
    print("\n[4/9] Building final ML dataset...")

    # Merge clean data with RDKit descriptors
    ml_df = df_clean[df_clean["molecule_chembl_id"].isin(valid_ids)].copy()
    ml_df = ml_df.merge(descriptor_df, on="molecule_chembl_id", how="inner")
    ml_df = ml_df.reset_index(drop=True)

    # Save processed dataset (CSV)
    ml_df.to_csv(PROCESSED_DATASET_PATH, index=False)
    print(f"  Saved: {PROCESSED_DATASET_PATH}")
    print(f"  Dataset shape: {ml_df.shape}")

    # Save fingerprint matrix
    fp_ids_path = PROCESSED_DATA_DIR / FINGERPRINT_IDS_FILENAME
    fp_matrix_path = PROCESSED_DATA_DIR / FINGERPRINT_MATRIX_FILENAME
    np.save(str(fp_matrix_path), fp_matrix)
    with open(fp_ids_path, "w") as f:
        f.write("\n".join(valid_ids))
    print(f"  Saved: fingerprints {fp_matrix.shape} -> {fp_matrix_path.name}")

    # ── 5. Train/Val/Test split (molecule-level) ──────────────
    print("\n[5/9] Molecule-level train/val/test split...")
    print(f"  Random seed: {RANDOM_SEED}")
    print(f"  Split ratios: {TRAIN_RATIO:.0%} train / {VAL_RATIO:.0%} val / {TEST_RATIO:.0%} test")

    # All molecules shuffled at molecule level
    all_ids = ml_df["molecule_chembl_id"].values
    np.random.seed(RANDOM_SEED)

    # First split: train vs (val + test)
    train_ids, temp_ids = train_test_split(
        all_ids,
        test_size=(VAL_RATIO + TEST_RATIO),
        random_state=RANDOM_SEED,
    )
    # Second split: val vs test from the remaining
    val_ids, test_ids = train_test_split(
        temp_ids,
        test_size=TEST_RATIO / (VAL_RATIO + TEST_RATIO),
        random_state=RANDOM_SEED,
    )

    train_mask = ml_df["molecule_chembl_id"].isin(train_ids)
    val_mask   = ml_df["molecule_chembl_id"].isin(val_ids)
    test_mask  = ml_df["molecule_chembl_id"].isin(test_ids)

    df_train = ml_df[train_mask]
    df_val   = ml_df[val_mask]
    df_test  = ml_df[test_mask]

    print(f"  Train: {len(df_train):,} molecules ({100*len(df_train)/len(ml_df):.1f}%)")
    print(f"  Val:   {len(df_val):,} molecules ({100*len(df_val)/len(ml_df):.1f}%)")
    print(f"  Test:  {len(df_test):,} molecules ({100*len(df_test)/len(ml_df):.1f}%)")

    # Save split info
    split_info = {
        "random_seed": RANDOM_SEED,
        "train_ratio": TRAIN_RATIO,
        "val_ratio": VAL_RATIO,
        "test_ratio": TEST_RATIO,
        "n_train": int(len(df_train)),
        "n_val":   int(len(df_val)),
        "n_test":  int(len(df_test)),
        "train_ids": list(train_ids),
        "val_ids":   list(val_ids),
        "test_ids":  list(test_ids),
    }
    with open(PROCESSED_DATA_DIR / SPLIT_INFO_FILENAME, "w") as f:
        json.dump(split_info, f, indent=2)

    # ── Feature matrices ──────────────────────────────────────
    # Use RDKit descriptors for primary model
    X_train = df_train[DESCRIPTOR_COLUMNS].values
    X_val   = df_val[DESCRIPTOR_COLUMNS].values
    X_test  = df_test[DESCRIPTOR_COLUMNS].values

    y_train = df_train["pIC50"].values
    y_val   = df_val["pIC50"].values
    y_test  = df_test["pIC50"].values

    # Scale descriptors
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_val_scaled   = scaler.transform(X_val)
    X_test_scaled  = scaler.transform(X_test)
    joblib.dump(scaler, SCALER_PATH)
    print(f"\n  Scaler saved: {SCALER_PATH.name}")

    # ── 6. Train Random Forest ────────────────────────────────
    print("\n[6/9] Training Random Forest Regressor...")
    print(f"  Hyperparameters: {RF_HYPERPARAMS}")
    t0 = time.time()
    rf_model = RandomForestRegressor(**RF_HYPERPARAMS)
    rf_model.fit(X_train_scaled, y_train)
    rf_train_time = time.time() - t0
    print(f"  Training time: {rf_train_time:.1f}s")

    joblib.dump(rf_model, RF_MODEL_PATH)
    print(f"  Saved: {RF_MODEL_PATH.name}")

    # Validate RF
    rf_val_pred = rf_model.predict(X_val_scaled)
    rf_val_mae  = mean_absolute_error(y_val, rf_val_pred)
    print(f"  Validation MAE: {rf_val_mae:.4f}")

    # ── 7. Train XGBoost ──────────────────────────────────────
    print("\n[7/9] Training XGBoost Regressor...")
    if not XGBOOST_AVAILABLE:
        logger.error("XGBoost not available. Skipping.")
        xgb_metrics = {"MAE": None, "RMSE": None, "R2": None}
    else:
        print(f"  Hyperparameters: {XGB_HYPERPARAMS}")
        t0 = time.time()
        xgb_model = xgb.XGBRegressor(**XGB_HYPERPARAMS)
        xgb_model.fit(
            X_train_scaled, y_train,
            eval_set=[(X_val_scaled, y_val)],
            verbose=False,
        )
        xgb_train_time = time.time() - t0
        print(f"  Training time: {xgb_train_time:.1f}s")

        joblib.dump(xgb_model, XGB_MODEL_PATH)
        print(f"  Saved: {XGB_MODEL_PATH.name}")

        xgb_val_pred = xgb_model.predict(X_val_scaled)
        xgb_val_mae  = mean_absolute_error(y_val, xgb_val_pred)
        print(f"  Validation MAE: {xgb_val_mae:.4f}")

    # ── 8. Evaluate on held-out TEST set ─────────────────────
    print("\n[8/9] Evaluating on held-out test set...")
    rf_metrics  = evaluate_model(rf_model, X_test_scaled, y_test)
    print(f"  Random Forest  - MAE: {rf_metrics['MAE']:.4f}  RMSE: {rf_metrics['RMSE']:.4f}  R2: {rf_metrics['R2']:.4f}")

    if XGBOOST_AVAILABLE:
        xgb_metrics = evaluate_model(xgb_model, X_test_scaled, y_test)
        print(f"  XGBoost        - MAE: {xgb_metrics['MAE']:.4f}  RMSE: {xgb_metrics['RMSE']:.4f}  R2: {xgb_metrics['R2']:.4f}")

    # Determine best model
    if XGBOOST_AVAILABLE:
        best_model = "XGBoost" if xgb_metrics["R2"] >= rf_metrics["R2"] else "RandomForest"
    else:
        best_model = "RandomForest"

    print(f"\n  Best model (by R²): {best_model}")

    # ── 9. Save results ───────────────────────────────────────
    print("\n[9/9] Saving training results...")
    training_results = {
        "metadata": {
            "training_date": datetime.utcnow().isoformat() + "Z",
            "dataset": RAW_DATASET_PATH.name,
            "dataset_source": DATASET_SOURCE,
            "target": DATASET_TARGET,
            "target_chembl_id": DATASET_TARGET_CHEMBL_ID,
            "chembl_version": DATASET_CHEMBL_VERSION,
            "random_seed": RANDOM_SEED,
            "feature_type": "rdkit_descriptors",
            "features_used": DESCRIPTOR_COLUMNS,
            "morgan_radius": MORGAN_RADIUS,
            "morgan_nbits": MORGAN_NBITS,
        },
        "dataset_stats": {
            "initial_records": prep_report["initial_records"],
            "final_molecules": prep_report["final_records"],
            "valid_rdkit_molecules": feat_stats["valid_molecules"],
            "invalid_rdkit_molecules": feat_stats["invalid_molecules"],
            "n_train": int(len(df_train)),
            "n_val": int(len(df_val)),
            "n_test": int(len(df_test)),
        },
        "models": {
            "RandomForest": {
                "hyperparameters": RF_HYPERPARAMS,
                "model_file": RF_MODEL_PATH.name,
                "test_metrics": rf_metrics,
                "training_time_seconds": float(rf_train_time),
            },
            "XGBoost": {
                "hyperparameters": XGB_HYPERPARAMS,
                "model_file": XGB_MODEL_PATH.name if XGBOOST_AVAILABLE else None,
                "test_metrics": xgb_metrics if XGBOOST_AVAILABLE else {},
                "training_time_seconds": float(xgb_train_time) if XGBOOST_AVAILABLE else None,
            },
        },
        "best_model_by_r2": best_model,
    }

    with open(TRAINING_RESULTS_PATH, "w") as f:
        json.dump(training_results, f, indent=2)
    print(f"  Saved: {TRAINING_RESULTS_PATH}")

    # ── Final summary ─────────────────────────────────────────
    total_time = time.time() - start_time
    print("\n" + "=" * 60)
    print("TRAINING COMPLETE")
    print("=" * 60)
    print(f"\nDataset:    {RAW_DATASET_PATH.name}")
    print(f"Source:     {DATASET_SOURCE}")
    print(f"Target:     {DATASET_TARGET} ({DATASET_TARGET_CHEMBL_ID})")
    print(f"\nRaw records:         {prep_report['initial_records']:,}")
    print(f"Final molecules:     {prep_report['final_records']:,}")
    print(f"Valid SMILES:        {feat_stats['valid_molecules']:,}")
    print(f"Invalid (RDKit):     {feat_stats['invalid_molecules']:,}")
    print(f"\nTrain:  {len(df_train):,} molecules")
    print(f"Val:    {len(df_val):,} molecules")
    print(f"Test:   {len(df_test):,} molecules")
    print(f"\n{'Model':<20} {'MAE':>8} {'RMSE':>8} {'R2':>8}")
    print("-" * 48)
    print(f"{'Random Forest':<20} {rf_metrics['MAE']:>8.4f} {rf_metrics['RMSE']:>8.4f} {rf_metrics['R2']:>8.4f}")
    if XGBOOST_AVAILABLE:
        print(f"{'XGBoost':<20} {xgb_metrics['MAE']:>8.4f} {xgb_metrics['RMSE']:>8.4f} {xgb_metrics['R2']:>8.4f}")
    print("-" * 48)
    print(f"\nBest model (R2): {best_model}")
    print(f"Total time:      {total_time:.1f}s")
    print("\nGenerated files:")
    print(f"  {PROCESSED_DATASET_PATH}")
    print(f"  {PROCESSED_DATA_DIR / FINGERPRINT_MATRIX_FILENAME}")
    print(f"  {RF_MODEL_PATH}")
    if XGBOOST_AVAILABLE:
        print(f"  {XGB_MODEL_PATH}")
    print(f"  {SCALER_PATH}")
    print(f"  {TRAINING_RESULTS_PATH}")
    print()

    return training_results


if __name__ == "__main__":
    results = main()
    sys.exit(0)
