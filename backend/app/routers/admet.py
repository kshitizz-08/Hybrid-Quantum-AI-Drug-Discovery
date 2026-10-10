"""
ADMET Router — Toxicity and Solubility screening endpoints.
"""
import logging
import pandas as pd
from pathlib import Path
from typing import Optional, List
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.routers.auth import get_current_user
from app.services.experiment_service import get_experiment
from app.services.admet_service import (
    run_admet_screening, predict_toxicity, predict_solubility, load_admet_metadata,
)
from app.config import get_settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/experiments", tags=["admet"])
settings = get_settings()

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent


def _get_egfr_ml_dataset() -> pd.DataFrame:
    proc_dir = Path(settings.data_processed_path).resolve()
    if not proc_dir.exists():
        proc_dir = PROJECT_ROOT / "data" / "processed"
    path = proc_dir / "EGFR_ML_dataset.csv"
    if not path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="EGFR_ML_dataset.csv not found. Run Milestone 3 training first.",
        )
    return pd.read_csv(path)


def _tox_label(tox_prob, threshold=0.5):
    if tox_prob is None or (isinstance(tox_prob, float) and pd.isna(tox_prob)):
        return "Unavailable"
    return "Toxic Risk" if tox_prob >= threshold else "Safe"


def _sol_label(log_sol):
    if log_sol is None or (isinstance(log_sol, float) and pd.isna(log_sol)):
        return "Unavailable"
    if log_sol > -4:
        return "Good"
    elif log_sol > -6:
        return "Moderate"
    return "Poor"


@router.get("/{experiment_id}/admet/models")
def get_admet_model_info(
    experiment_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get ADMET model metadata (training datasets, metrics, hyperparameters)."""
    get_experiment(db, experiment_id, current_user.id)
    meta = load_admet_metadata()
    return {
        "experiment_id": experiment_id,
        "toxicity_model": meta.get("toxicity"),
        "solubility_model": meta.get("solubility"),
    }


@router.post("/{experiment_id}/admet")
def run_admet(
    experiment_id: int,
    top_n_input: int = Query(100, ge=10, le=500, description="Top N by pIC50 to screen"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Run ADMET screening on top N EGFR candidates.
    Predicts NR-AR toxicity (Tox21) and log solubility (ESOL) for each molecule.
    Computes composite scoring formula (documented in ml/admet/scoring.py).

    Fallback: If RDKit is blocked by Windows Application Control policy,
    serves pre-computed results from EGFR_admet_results.csv instead of
    failing. The pre-computed file is the ground-truth data used for all
    downstream stages (quantum, docking, ranking).
    """
    get_experiment(db, experiment_id, current_user.id)

    proc_dir = PROJECT_ROOT / "data" / "processed"
    proc_dir.mkdir(exist_ok=True)
    precomputed_path = proc_dir / "EGFR_admet_results.csv"

    fallback_used = False
    df_admet = None

    # Try live screening first
    try:
        df_ml = _get_egfr_ml_dataset()
        df_admet = run_admet_screening(df_ml, top_n_input=top_n_input)
        # Save/overwrite results
        df_admet.to_csv(precomputed_path, index=False)
    except (ImportError, OSError) as rdkit_err:
        logger.warning(
            "ADMET live screening unavailable (%s). Using pre-computed results.", rdkit_err
        )
        if not precomputed_path.exists():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=(
                    f"ADMET screening failed: RDKit is blocked by the OS Application "
                    f"Control policy on this machine. Pre-computed fallback file not found "
                    f"at {precomputed_path}. Please provide EGFR_admet_results.csv."
                ),
            )
        df_admet = pd.read_csv(precomputed_path)
        fallback_used = True

    return {
        "status": "completed",
        "experiment_id": experiment_id,
        "total_screened": len(df_admet),
        "top_n_input": top_n_input,
        "fallback_used": fallback_used,
        "fallback_reason": (
            "RDKit DLLs blocked by Windows Application Control policy. "
            "Using pre-computed EGFR_admet_results.csv (50 molecules)."
            if fallback_used else None
        ),
        "toxicity_model": "Random Forest Classifier (Tox21 NR-AR)",
        "solubility_model": "Random Forest Regressor (Delaney ESOL)",
        "disclaimer": (
            "ADMET predictions are computational outputs and do not constitute "
            "experimental or clinical validation."
        ),
    }


@router.get("/{experiment_id}/admet")
def get_admet_results(
    experiment_id: int,
    min_pic50:        float = Query(5.0),
    max_tox_risk:     float = Query(1.0),
    min_log_sol:      float = Query(-10.0),
    require_lipinski: bool  = Query(False),
    limit:            int   = Query(50, ge=1, le=500),
    offset:           int   = Query(0, ge=0),
    search:           Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Get ADMET screening results with configurable filters and pagination.
    """
    get_experiment(db, experiment_id, current_user.id)

    proc_dir = PROJECT_ROOT / "data" / "processed"
    path = proc_dir / "EGFR_admet_results.csv"
    if not path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="ADMET results not found. Run POST /admet first.",
        )

    df = pd.read_csv(path)

    # Apply filters
    pic50_col = "predicted_pIC50" if "predicted_pIC50" in df.columns else "pIC50"
    df = df[df[pic50_col] >= min_pic50]

    if "tox_probability" in df.columns:
        df = df[df["tox_probability"].fillna(1.0) <= max_tox_risk]
    if "predicted_log_solubility" in df.columns:
        df = df[df["predicted_log_solubility"].fillna(-99.0) >= min_log_sol]
    if require_lipinski and "lipinski_pass" in df.columns:
        df = df[df["lipinski_pass"] == True]  # noqa: E712

    if search:
        s = search.lower()
        df = df[df["molecule_chembl_id"].str.lower().str.contains(s, na=False) |
                df["smiles"].str.lower().str.contains(s, na=False)]

    total = len(df)
    df = df.iloc[offset:offset + limit]

    molecules = []
    for _, row in df.iterrows():
        tox_p = row.get("tox_probability", None)
        tox_p = None if pd.isna(tox_p) else float(tox_p)
        log_s = row.get("predicted_log_solubility", None)
        log_s = None if pd.isna(log_s) else float(log_s)

        molecules.append({
            "molecule_chembl_id":       str(row["molecule_chembl_id"]),
            "smiles":                   str(row.get("smiles", "")),
            "predicted_pIC50":          float(row.get(pic50_col, 0)),
            "pIC50":                    float(row.get("pIC50", 0)),
            "tox_probability":          tox_p,
            "tox_prediction":           int(row.get("tox_prediction", -1)),
            "tox_label":                _tox_label(tox_p),
            "predicted_log_solubility": log_s,
            "solubility_label":         _sol_label(log_s),
            "composite_score":          float(row.get("composite_score", 0)),
            "bioactivity_norm":         float(row.get("bioactivity_norm", 0)),
            "toxicity_risk_norm":       float(row.get("toxicity_risk_norm", 0)),
            "solubility_norm":          float(row.get("solubility_norm", 0)),
            "drug_likeness_norm":       float(row.get("drug_likeness_norm", 0)),
            "lipinski_pass":            bool(row.get("lipinski_pass", False)),
            "molecular_weight":         float(row.get("molecular_weight", 0)),
            "logP":                     float(row.get("logP", 0)),
            "TPSA":                     float(row.get("TPSA", 0)),
            "HBD":                      int(row.get("HBD", 0)),
            "HBA":                      int(row.get("HBA", 0)),
        })

    return {
        "experiment_id": experiment_id,
        "total_filtered": total,
        "returned": len(molecules),
        "offset": offset,
        "filter_config": {
            "min_pic50": min_pic50,
            "max_tox_risk": max_tox_risk,
            "min_log_sol": min_log_sol,
            "require_lipinski": require_lipinski,
        },
        "score_formula": {
            "description": "composite = 0.4*bioactivity - 0.3*toxicity + 0.2*solubility + 0.1*drug_likeness",
            "reference": "ml/admet/scoring.py",
        },
        "molecules": molecules,
        "disclaimer": (
            "ADMET predictions are computational outputs and do not constitute "
            "experimental or clinical validation."
        ),
    }
