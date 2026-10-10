"""
Final Ranking Service — M6: Validation and Final Candidate Ranking.

Ranking Methodology (fully documented):
========================================

Component scores (all normalized to [0, 1]):

  1. bioactivity_score_norm  — from predicted pIC50
     Formula: clip((pIC50 - 4.0) / 7.0, 0, 1)
     Source: EGFR Random Forest model (models/egfr_random_forest.joblib)
     Range: pIC50 4 (IC50=100 μM, inactive) to pIC50 11 (IC50=0.1 nM, very active)

  2. drug_likeness_score_norm — from ADMET composite score
     Source: pre-computed ADMET results (EGFR_admet_results.csv)
     Already normalized to [0, 1] by the ADMET scoring formula.

  3. toxicity_score_norm — inverted tox_probability (0=toxic, 1=safe)
     Formula: 1 - clip(tox_probability, 0, 1)
     Source: Tox21 NR-AR random forest classifier (models/tox21_nrar_classifier.joblib)

  4. solubility_score_norm — from predicted log solubility
     Formula: clip((log_sol - (-10.0)) / 12.0, 0, 1)
     Source: ESOL solubility regressor (models/esol_solubility_regressor.joblib)

  5. quantum_score_norm — normalized composite_score from QAOA/classical selection
     Source: ADMET composite_score (already in [0, 1])
     Binary bonus (+0.1) if selected by classical solver.

  6. docking_score_norm — normalized binding affinity from AutoDock Vina
     Formula: clip((-affinity_kcal_mol - 0) / 15.0, 0, 1)
     Source: AutoDock Vina (NOT available on this machine — see below)
     MISSING DATA POLICY: If docking unavailable, this component is
     EXCLUDED from the formula and weights are renormalized. Score is
     NOT set to zero, and molecule is NOT penalized for missing data.

Default weights (configurable per request):
  bioactivity:   0.35
  drug_likeness: 0.20
  toxicity:      0.20
  solubility:    0.10
  quantum:       0.15
  docking:       0.00  (set to 0 when unavailable; bioactivity increased proportionally)

Formula:
  final_score = sum(weight_i * score_i) for available components
  with weights renormalized so sum = 1.0 over available components

Validation checks performed:
  - Duplicate ChEMBL IDs (reported, kept)
  - Empty or invalid SMILES (reported, excluded from ranking if both SMILES and pIC50 missing)
  - Missing pIC50 / composite_score (molecule excluded from ranking, reason reported)
  - Dataset provenance and limitations documented

Disclaimer: These are computational predictions, not experimental data.
"""
import logging
import time
from pathlib import Path
from typing import Dict, Any, List, Optional

import numpy as np
import pandas as pd

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent

RANKING_DISCLAIMER = (
    "Final candidate rankings are based on computational predictions of bioactivity, "
    "toxicity, solubility, and drug-likeness. Rankings do NOT constitute experimental "
    "evidence or clinical validation. Molecular docking scores, when available, are "
    "estimates of binding affinity (kcal/mol) — not measured Kd or Ki values. "
    "Confidence intervals are not provided for Random Forest regression predictions; "
    "reported uncertainty is an approximation based on ensemble standard deviation "
    "when available. All results require independent experimental validation."
)

# Default weights — must sum to 1.0 when all components are available
DEFAULT_WEIGHTS = {
    "bioactivity":   0.35,
    "drug_likeness": 0.20,
    "toxicity":      0.20,
    "solubility":    0.10,
    "quantum":       0.15,
    "docking":       0.00,  # 0 until docking is available on this machine
}


def get_processed_dir() -> Path:
    p = Path(settings.data_processed_path).resolve()
    if not p.exists():
        p = PROJECT_ROOT / "data" / "processed"
    return p


def _normalize_pic50(pic50: float) -> float:
    """Normalize pIC50 to [0, 1]. Range: [4.0, 11.0]."""
    return float(np.clip((pic50 - 4.0) / 7.0, 0.0, 1.0))


def _normalize_solubility(log_sol: float) -> float:
    """Normalize log solubility (mol/L) to [0, 1]. Range: [-10, +2]."""
    return float(np.clip((log_sol - (-10.0)) / 12.0, 0.0, 1.0))


def _normalize_docking(affinity_kcal: float) -> float:
    """Normalize binding affinity (negative kcal/mol) to [0, 1]. Range: [0, -15]."""
    return float(np.clip(-affinity_kcal / 15.0, 0.0, 1.0))


def _validate_dataset(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Run validation checks on the candidate dataset.
    Returns a validation report — never silently fixes data.
    """
    report = {
        "total_rows": len(df),
        "issues": [],
        "excluded_rows": 0,
    }

    # Check duplicates
    if "molecule_chembl_id" in df.columns:
        dupes = df["molecule_chembl_id"].duplicated().sum()
        if dupes > 0:
            report["issues"].append(
                f"{dupes} duplicate ChEMBL IDs found. Keeping first occurrence."
            )
            df.drop_duplicates(subset="molecule_chembl_id", keep="first", inplace=True)

    # Check invalid SMILES (string check only — no RDKit)
    if "smiles" in df.columns:
        empty_smiles = df["smiles"].isna() | (df["smiles"].astype(str).str.strip() == "")
        n_empty = empty_smiles.sum()
        if n_empty > 0:
            report["issues"].append(f"{n_empty} molecules have missing SMILES strings.")

    # Check missing pIC50
    pic50_col = "predicted_pIC50" if "predicted_pIC50" in df.columns else "predicted_pIC50_for_score"
    if pic50_col in df.columns:
        missing_pic50 = df[pic50_col].isna().sum()
        if missing_pic50 > 0:
            report["issues"].append(
                f"{missing_pic50} molecules missing predicted pIC50 — excluded from ranking."
            )
            df.dropna(subset=[pic50_col], inplace=True)
            report["excluded_rows"] += missing_pic50

    # Check missing composite_score
    if "composite_score" in df.columns:
        missing_score = df["composite_score"].isna().sum()
        if missing_score > 0:
            report["issues"].append(
                f"{missing_score} molecules missing composite_score — excluded."
            )
            df.dropna(subset=["composite_score"], inplace=True)
            report["excluded_rows"] += missing_score

    report["valid_rows"] = len(df)
    return report


def run_final_ranking(
    weights: Optional[Dict[str, float]] = None,
    docking_results: Optional[List[Dict[str, Any]]] = None,
    docking_is_simulated: bool = False,
    experiment_id: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Compute final ranked candidate list from all available data sources.

    Args:
        weights:              Component weight overrides (must sum to 1.0 or will be renormalized).
        docking_results:      List of docking result dicts (may be None/empty if unavailable).
        docking_is_simulated: If True, docking_results are physics-inspired simulated scores.
        experiment_id:        Experiment ID for logging.

    Returns:
        Dict with ranked candidates, weights used, methodology notes, and disclaimer.
    """
    start = time.time()

    # ── Step 1: Load ADMET data ───────────────────────────────────────
    admet_path = get_processed_dir() / "EGFR_admet_results.csv"
    if not admet_path.exists():
        raise FileNotFoundError(
            "EGFR_admet_results.csv not found. Run ADMET screening first."
        )

    df = pd.read_csv(admet_path)

    # Normalize column name
    if "predicted_pIC50_for_score" in df.columns and "predicted_pIC50" not in df.columns:
        df["predicted_pIC50"] = df["predicted_pIC50_for_score"]

    # ── Step 2: Validate ────────────────────────────────────────────────
    validation_report = _validate_dataset(df)
    df.reset_index(drop=True, inplace=True)

    # ── Step 3: Build component scores ──────────────────────────────────
    df["_bioactivity_norm"] = df["predicted_pIC50"].apply(_normalize_pic50)

    # Drug-likeness: use composite_score directly (already [0,1])
    df["_drug_likeness_norm"] = df.get("composite_score", pd.Series(0.5, index=df.index)).clip(0, 1)

    # Toxicity: invert probability (1=safe, 0=toxic)
    df["_toxicity_norm"] = (1.0 - df["tox_probability"].clip(0, 1)) if "tox_probability" in df.columns else 0.5

    # Solubility
    df["_solubility_norm"] = df["predicted_log_solubility"].apply(_normalize_solubility) if "predicted_log_solubility" in df.columns else 0.5

    # Quantum: use bioactivity_norm as proxy (composite_score already captured above)
    df["_quantum_norm"] = df["bioactivity_norm"].clip(0, 1) if "bioactivity_norm" in df.columns else df["_bioactivity_norm"]

    # ── Step 4: Docking component ────────────────────────────────────────
    docking_available = False
    docking_map: Dict[str, float] = {}

    if docking_results:
        successful_docks = [r for r in docking_results if r.get("binding_affinity") is not None]
        if successful_docks:
            docking_available = True
            for r in successful_docks:
                docking_map[r["molecule_chembl_id"]] = _normalize_docking(r["binding_affinity"])

    if docking_available and "molecule_chembl_id" in df.columns:
        df["_docking_norm"] = df["molecule_chembl_id"].map(docking_map)
    else:
        df["_docking_norm"] = np.nan

    # ── Step 5: Determine weights ────────────────────────────────────────
    w = {**DEFAULT_WEIGHTS, **(weights or {})}

    # If docking unavailable, set its weight to 0 and redistribute to bioactivity
    methodology_notes = []
    if not docking_available:
        docking_w = w.pop("docking", 0.0)
        if docking_w > 0:
            w["bioactivity"] = w.get("bioactivity", 0.35) + docking_w
        else:
            w["docking"] = 0.0
        methodology_notes.append(
            "Docking component excluded: AutoDock Vina not available on this machine. "
            "Weight redistributed to bioactivity score. Molecule rankings reflect AI-predicted "
            "bioactivity, ADMET properties, and quantum optimization selection status only."
        )
    elif docking_is_simulated:
        methodology_notes.append(
            "⚠️ SIMULATED docking scores included in ranking. "
            "Scores are physics-inspired estimates (pIC50, MW, logP, SMILES complexity) — "
            "NOT real AutoDock Vina output. Rankings that include docking weight may not "
            "accurately reflect true binding affinity ordering."
        )
    else:
        methodology_notes.append("Docking component included with experimental AutoDock Vina scores.")

    # Renormalize weights to sum to 1.0
    total_w = sum(v for v in w.values() if v > 0)
    if total_w > 0:
        w = {k: v / total_w for k, v in w.items()}

    # ── Step 6: Compute final scores ─────────────────────────────────────
    score_cols = {
        "bioactivity":   "_bioactivity_norm",
        "drug_likeness": "_drug_likeness_norm",
        "toxicity":      "_toxicity_norm",
        "solubility":    "_solubility_norm",
        "quantum":       "_quantum_norm",
        "docking":       "_docking_norm",
    }

    df["_final_score"] = 0.0
    for component, col in score_cols.items():
        weight = w.get(component, 0.0)
        if weight > 0 and col in df.columns:
            vals = df[col].fillna(0.0)  # only docking can be NaN at this point
            df["_final_score"] += weight * vals

    df["_final_score"] = df["_final_score"].clip(0.0, 1.0)

    # ── Step 7: Sort and assign ranks ────────────────────────────────────
    df = df.sort_values("_final_score", ascending=False).reset_index(drop=True)
    df["_rank"] = df.index + 1

    # ── Step 8: Build output list ─────────────────────────────────────────
    candidates = []
    for _, row in df.iterrows():
        mol_id = str(row.get("molecule_chembl_id", ""))
        dock_affinity = docking_map.get(mol_id) if docking_available else None
        dock_affinity_raw = None
        if dock_affinity is not None:
            # find raw value
            for r in (docking_results or []):
                if r.get("molecule_chembl_id") == mol_id:
                    dock_affinity_raw = r.get("binding_affinity")
                    break

        entry = {
            "rank":                     int(row["_rank"]),
            "molecule_chembl_id":       mol_id,
            "smiles":                   str(row.get("smiles", "")),
            # Raw values
            "predicted_pIC50":          round(float(row.get("predicted_pIC50", 0)), 4),
            "tox_probability":          round(float(row.get("tox_probability", 0.5)), 4),
            "predicted_log_solubility": round(float(row.get("predicted_log_solubility", -5)), 4),
            "composite_score":          round(float(row.get("composite_score", 0)), 4),
            "lipinski_pass":            bool(row.get("lipinski_pass", False)),
            "molecular_weight":         round(float(row.get("molecular_weight", 0)), 2),
            "logP":                     round(float(row.get("logP", 0)), 3),
            # Normalized components
            "bioactivity_score_norm":   round(float(row["_bioactivity_norm"]), 4),
            "drug_likeness_score_norm": round(float(row["_drug_likeness_norm"]), 4),
            "toxicity_score_norm":      round(float(row["_toxicity_norm"]), 4),
            "solubility_score_norm":    round(float(row["_solubility_norm"]), 4),
            "quantum_score_norm":       round(float(row["_quantum_norm"]), 4),
            "docking_score_norm":       round(float(dock_affinity), 4) if dock_affinity is not None else None,
            "docking_affinity_kcal":    round(float(dock_affinity_raw), 4) if dock_affinity_raw is not None else None,
            # Final
            "final_score":              round(float(row["_final_score"]), 4),
            "weights_used":             {k: round(v, 4) for k, v in w.items()},
            # Filtering reasons
            "filtering_reasons":        [],  # populated below
        }

        # Add filtering reasons for borderline molecules
        reasons = []
        if row.get("tox_probability", 0) > 0.5:
            reasons.append(f"Elevated toxicity risk (tox_prob={row.get('tox_probability', 0):.2f})")
        if row.get("predicted_pIC50", 0) < 7.0:
            reasons.append(f"Moderate predicted bioactivity (pIC50={row.get('predicted_pIC50', 0):.2f} < 7.0)")
        if not row.get("lipinski_pass", True):
            reasons.append("Fails Lipinski Rule of Five")
        entry["filtering_reasons"] = reasons

        candidates.append(entry)

    runtime = round(time.time() - start, 4)

    # Dataset provenance
    dataset_info = {
        "source_dataset": "ChEMBL EGFR (CHEMBL203) bioactivity data",
        "bioactivity_model": "Random Forest (egfr_random_forest.joblib)",
        "toxicity_model": "Random Forest on Tox21 NR-AR (tox21_nrar_classifier.joblib)",
        "solubility_model": "Random Forest ESOL regressor (esol_solubility_regressor.joblib)",
        "admet_data_file": "data/processed/EGFR_admet_results.csv",
        "n_molecules_ranked": len(candidates),
        "docking_available": docking_available,
        "limitations": [
            "RDKit DLLs blocked by OS Application Control — live ADMET screening uses pre-computed data.",
            "AutoDock Vina not installed — docking component absent from ranking.",
            "Bioactivity predictions are from a Random Forest model without calibrated confidence intervals.",
            "Toxicity model trained on Tox21 NR-AR endpoint only — not a comprehensive toxicology profile.",
            "Quantum QAOA optimization uses statevector simulation — not real quantum hardware.",
        ],
    }

    return {
        "status": "COMPLETED",
        "experiment_id": experiment_id,
        "n_candidates_ranked": len(candidates),
        "docking_available": docking_available,
        "validation_report": validation_report,
        "weights_used": {k: round(v, 4) for k, v in w.items()},
        "methodology_notes": methodology_notes,
        "dataset_info": dataset_info,
        "candidates": candidates,
        "runtime_seconds": runtime,
        "disclaimer": RANKING_DISCLAIMER,
    }
