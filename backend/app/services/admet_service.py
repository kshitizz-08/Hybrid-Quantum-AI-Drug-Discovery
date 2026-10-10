"""
ADMET Service — Predict toxicity and solubility for EGFR candidate molecules.
"""
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

import numpy as np
import pandas as pd
import joblib
from fastapi import HTTPException, status

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent


def _get_admet_model_dir() -> Path:
    p = Path(settings.models_path).resolve()
    if not p.exists():
        p = PROJECT_ROOT / "models"
    return p


def _get_processed_dir() -> Path:
    p = Path(settings.data_processed_path).resolve()
    if not p.exists():
        p = PROJECT_ROOT / "data" / "processed"
    return p


def _require_file(path: Path, label: str) -> None:
    if not path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                f"{label} not found at {path.name}. "
                "Run 'python scripts/train_admet_models.py' first."
            ),
        )


def load_admet_metadata() -> Dict[str, Any]:
    """Load Tox21 and ESOL training result metadata."""
    models_dir = _get_admet_model_dir()
    out = {}
    for key, fname in [("toxicity", "tox21_training_results.json"),
                       ("solubility", "esol_training_results.json")]:
        p = models_dir / fname
        if p.exists():
            with open(p, "r", encoding="utf-8") as f:
                out[key] = json.load(f)
        else:
            out[key] = None
    return out


def _extract_rdkit_features_for_smiles(smiles_list: List[str]) -> np.ndarray:
    """Extract 8 RDKit descriptors for a list of SMILES strings."""
    from rdkit import Chem
    from rdkit.Chem import Descriptors, rdMolDescriptors

    rows = []
    for smi in smiles_list:
        mol = Chem.MolFromSmiles(smi) if isinstance(smi, str) else None
        if mol is None:
            rows.append([np.nan] * 8)
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
    return np.array(rows, dtype=np.float32)


def _extract_rdkit_descriptor_fp_features(smiles_list: List[str]) -> np.ndarray:
    """Extract 8 descriptors + 2048 Morgan bits (for toxicity classifier)."""
    from rdkit import Chem
    from rdkit.Chem import Descriptors, rdMolDescriptors, rdFingerprintGenerator

    fp_gen = rdFingerprintGenerator.GetMorganGenerator(radius=2, fpSize=2048)
    rows = []
    for smi in smiles_list:
        mol = Chem.MolFromSmiles(smi) if isinstance(smi, str) else None
        if mol is None:
            rows.append(np.full(8 + 2048, np.nan))
            continue
        desc = [
            Descriptors.MolWt(mol), Descriptors.MolLogP(mol),
            Descriptors.TPSA(mol), rdMolDescriptors.CalcNumHBD(mol),
            rdMolDescriptors.CalcNumHBA(mol),
            rdMolDescriptors.CalcNumRotatableBonds(mol),
            rdMolDescriptors.CalcNumRings(mol),
            rdMolDescriptors.CalcFractionCSP3(mol),
        ]
        fp = fp_gen.GetFingerprintAsNumPy(mol).astype(np.float32)
        rows.append(np.concatenate([desc, fp]))
    return np.array(rows, dtype=np.float32)


def predict_toxicity(smiles_list: List[str]) -> Dict[str, Any]:
    """
    Predict NR-AR toxicity probability for each SMILES.
    Returns probabilities (0=safe, 1=toxic) and binary predictions.
    """
    models_dir = _get_admet_model_dir()
    model_path  = models_dir / "tox21_nrar_classifier.joblib"
    scaler_path = models_dir / "tox21_nrar_scaler.joblib"
    _require_file(model_path, "Toxicity model")
    _require_file(scaler_path, "Toxicity scaler")

    clf    = joblib.load(model_path)
    scaler = joblib.load(scaler_path)

    X = _extract_rdkit_descriptor_fp_features(smiles_list)

    # Handle molecules that failed RDKit parsing
    valid_mask = ~np.any(np.isnan(X), axis=1)
    probabilities = np.full(len(smiles_list), np.nan)
    predictions   = np.full(len(smiles_list), -1, dtype=int)

    if valid_mask.sum() > 0:
        X_valid = scaler.transform(X[valid_mask])
        proba_valid = clf.predict_proba(X_valid)[:, 1]
        pred_valid  = clf.predict(X_valid)
        probabilities[valid_mask] = proba_valid
        predictions[valid_mask]   = pred_valid

    return {
        "probabilities": probabilities.tolist(),
        "predictions":   predictions.tolist(),
        "model":         "Random Forest Classifier (Tox21 NR-AR)",
        "n_valid":       int(valid_mask.sum()),
        "n_invalid":     int((~valid_mask).sum()),
    }


def predict_solubility(smiles_list: List[str]) -> Dict[str, Any]:
    """
    Predict log solubility (mol/L) for each SMILES using ESOL RF model.
    """
    models_dir = _get_admet_model_dir()
    model_path  = models_dir / "esol_solubility_regressor.joblib"
    scaler_path = models_dir / "esol_solubility_scaler.joblib"
    _require_file(model_path, "Solubility model")
    _require_file(scaler_path, "Solubility scaler")

    reg    = joblib.load(model_path)
    scaler = joblib.load(scaler_path)

    X = _extract_rdkit_features_for_smiles(smiles_list)

    valid_mask = ~np.any(np.isnan(X), axis=1)
    log_sol = np.full(len(smiles_list), np.nan)

    if valid_mask.sum() > 0:
        X_valid = scaler.transform(X[valid_mask])
        log_sol[valid_mask] = reg.predict(X_valid)

    return {
        "log_solubility": log_sol.tolist(),
        "model":          "Random Forest Regressor (Delaney ESOL)",
        "units":          "log10(mol/L)",
        "n_valid":        int(valid_mask.sum()),
        "n_invalid":      int((~valid_mask).sum()),
    }


def run_admet_screening(
    df_ml: pd.DataFrame,
    top_n_input: int = 100,
) -> pd.DataFrame:
    """
    Run full ADMET screening on top N EGFR candidates.

    Input: EGFR_ML_dataset.csv with predicted_pIC50 column (or pIC50 as proxy).
    Output: DataFrame with toxicity and solubility predictions + composite scores.
    """
    from ml.admet.scoring import compute_composite_score

    # Start from top N by predicted pIC50 (or actual pIC50)
    pic50_col = "predicted_pIC50" if "predicted_pIC50" in df_ml.columns else "pIC50"
    df_top = df_ml.nlargest(top_n_input, pic50_col).copy().reset_index(drop=True)

    logger.info("Running ADMET screening on %d candidates...", len(df_top))
    smiles_list = df_top["smiles"].tolist()

    # Toxicity predictions
    tox_result = predict_toxicity(smiles_list)
    df_top["tox_probability"]  = tox_result["probabilities"]
    df_top["tox_prediction"]   = tox_result["predictions"]

    # Solubility predictions
    sol_result = predict_solubility(smiles_list)
    df_top["predicted_log_solubility"] = sol_result["log_solubility"]

    # Use predicted_pIC50 or pIC50
    df_top["predicted_pIC50_for_score"] = (
        df_top["predicted_pIC50"] if "predicted_pIC50" in df_top.columns else df_top["pIC50"]
    )

    # Compute composite scores
    composite_scores = []
    for _, row in df_top.iterrows():
        pic50  = row["predicted_pIC50_for_score"] if not pd.isna(row["predicted_pIC50_for_score"]) else 5.0
        tox    = row["tox_probability"] if not pd.isna(row["tox_probability"]) else 0.5
        log_s  = row["predicted_log_solubility"] if not pd.isna(row["predicted_log_solubility"]) else -5.0
        lip    = bool(row.get("lipinski_pass", False))
        scores = compute_composite_score(pic50, tox, log_s, lip)
        composite_scores.append(scores)

    scores_df = pd.DataFrame(composite_scores)
    for col in scores_df.columns:
        df_top[col] = scores_df[col].values

    df_top = df_top.sort_values("composite_score", ascending=False).reset_index(drop=True)
    logger.info("ADMET screening complete: %d molecules processed", len(df_top))
    return df_top
