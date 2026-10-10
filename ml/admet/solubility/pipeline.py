"""
Solubility Prediction Pipeline — Delaney ESOL Dataset.

Dataset:
  Name:     Delaney ESOL (Estimated SOLubility)
  Source:   Delaney, J.S. (2004). ESOL: Estimating Aqueous Solubility Directly
            from Molecular Structure. J. Chem. Inf. Comput. Sci., 44(3), 1000-1005.
  File:     data/raw/delaney-processed.csv (deepchem mirror)
  Target:   'measured log solubility in mols per litre' (log10 mol/L)
  Size:     1,128 molecules; 0 missing values.

Features:
  8 RDKit physicochemical descriptors: MW, LogP, TPSA, HBD, HBA,
  RotBonds, RingCount, FractionCsp3.
  (Same descriptor set as EGFR model — trained separately on ESOL data.)

Evaluation:
  MAE, RMSE, R²
"""
import json
import logging
from pathlib import Path
from typing import Dict, Any, Tuple

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, root_mean_squared_error, r2_score
from sklearn.preprocessing import StandardScaler
import joblib

logger = logging.getLogger(__name__)


def load_and_inspect_esol(path: Path) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Load Delaney ESOL dataset and return inspection report.
    """
    if not path.exists():
        raise FileNotFoundError(
            f"ESOL dataset not found at {path}. "
            "Download from deepchem GitHub: datasets/delaney-processed.csv"
        )

    df = pd.read_csv(path)
    target_col = "measured log solubility in mols per litre"
    smiles_col = "smiles"

    report = {
        "source": "Delaney ESOL (2004)",
        "citation": (
            "Delaney, J.S. (2004). ESOL: Estimating Aqueous Solubility Directly from "
            "Molecular Structure. J. Chem. Inf. Comput. Sci., 44(3), 1000-1005."
        ),
        "file": path.name,
        "total_rows": int(len(df)),
        "total_columns": int(len(df.columns)),
        "columns": list(df.columns),
        "smiles_present": int(df[smiles_col].notna().sum()),
        "smiles_missing": int(df[smiles_col].isna().sum()),
        "target_column": target_col,
        "target_units": "log10(mol/L)",
        "target_stats": {
            "min":    float(df[target_col].min()),
            "max":    float(df[target_col].max()),
            "mean":   float(df[target_col].mean()),
            "median": float(df[target_col].median()),
            "std":    float(df[target_col].std()),
        },
        "missing_target": int(df[target_col].isna().sum()),
    }
    return df, report


def extract_rdkit_features(smiles_list: list) -> Tuple[np.ndarray, list]:
    """
    Extract 8 RDKit physicochemical descriptors for each SMILES.
    Returns (feature_matrix, valid_indices).
    """
    from rdkit import Chem
    from rdkit.Chem import Descriptors, rdMolDescriptors

    rows = []
    valid_idx = []

    for i, smi in enumerate(smiles_list):
        if not isinstance(smi, str) or not smi.strip():
            continue
        mol = Chem.MolFromSmiles(smi)
        if mol is None:
            continue
        rows.append([
            Descriptors.MolWt(mol),
            Descriptors.MolLogP(mol),
            Descriptors.TPSA(mol),
            rdMolDescriptors.CalcNumHBD(mol),
            rdMolDescriptors.CalcNumHBA(mol),
            rdMolDescriptors.CalcNumRotatableBonds(mol),
            rdMolDescriptors.CalcNumRings(mol),
            rdMolDescriptors.CalcFractionCSP3(mol),
        ])
        valid_idx.append(i)

    return np.array(rows, dtype=np.float32), valid_idx


def train_solubility_model(
    esol_path: Path,
    model_path: Path,
    scaler_path: Path,
    results_path: Path,
    random_seed: int = 42,
    hyperparams: dict = None,
) -> Dict[str, Any]:
    """
    Full solubility regression model training pipeline.
    Returns evaluation results (all from real data — no fabrication).
    """
    from ml.admet.config import (
        SOL_RF_HYPERPARAMS, SOL_TRAIN_RATIO, SOL_TEST_RATIO, ESOL_TARGET_COL
    )

    if hyperparams is None:
        hyperparams = SOL_RF_HYPERPARAMS

    logger.info("Loading ESOL dataset: %s", esol_path)
    df, inspection = load_and_inspect_esol(esol_path)

    target_col = ESOL_TARGET_COL
    smiles_col = "smiles"

    # Drop any rows with missing target or SMILES
    df_clean = df[[smiles_col, target_col]].dropna().reset_index(drop=True)
    logger.info("Clean rows: %d / %d", len(df_clean), len(df))

    smiles_list = df_clean[smiles_col].tolist()
    logger.info("Extracting RDKit descriptors for %d molecules...", len(smiles_list))
    X, valid_idx = extract_rdkit_features(smiles_list)
    df_valid = df_clean.iloc[valid_idx].reset_index(drop=True)
    y = df_valid[target_col].values.astype(np.float32)

    n_invalid = len(df_clean) - len(valid_idx)
    logger.info("Valid molecules: %d | Invalid SMILES: %d", len(valid_idx), n_invalid)

    # Train/test split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=SOL_TEST_RATIO, random_state=random_seed
    )

    # Scale
    scaler = StandardScaler()
    X_train_sc = scaler.fit_transform(X_train)
    X_test_sc  = scaler.transform(X_test)
    joblib.dump(scaler, scaler_path)

    # Train
    logger.info("Training Random Forest Regressor for solubility...")
    reg = RandomForestRegressor(**hyperparams)
    reg.fit(X_train_sc, y_train)
    joblib.dump(reg, model_path)

    # Evaluate
    y_pred = reg.predict(X_test_sc)
    mae  = float(mean_absolute_error(y_test, y_pred))
    rmse = float(root_mean_squared_error(y_test, y_pred))
    r2   = float(r2_score(y_test, y_pred))

    metrics = {
        "MAE":  mae,
        "RMSE": rmse,
        "R2":   r2,
        "n_test_samples":  int(len(y_test)),
        "n_train_samples": int(len(y_train)),
    }

    results = {
        "metadata": {
            "dataset": esol_path.name,
            "source": inspection["source"],
            "target_column": target_col,
            "target_units": "log10(mol/L)",
            "random_seed": random_seed,
            "n_features": int(X.shape[1]),
            "feature_description": "8 RDKit physicochemical descriptors",
            "features_used": [
                "molecular_weight", "logP", "TPSA", "HBD", "HBA",
                "rotatable_bonds", "ring_count", "fraction_csp3"
            ],
            "train_ratio": SOL_TRAIN_RATIO,
            "test_ratio": SOL_TEST_RATIO,
            "hyperparameters": hyperparams,
            "model_file": model_path.name,
            "invalid_smiles": n_invalid,
        },
        "inspection": inspection,
        "metrics": metrics,
    }

    results_path.parent.mkdir(parents=True, exist_ok=True)
    with open(results_path, "w") as f:
        json.dump(results, f, indent=2, default=str)

    logger.info(
        "Solubility model trained: MAE=%.4f | RMSE=%.4f | R2=%.4f",
        mae, rmse, r2,
    )
    return results
