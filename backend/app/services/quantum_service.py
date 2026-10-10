"""
Quantum Optimization Service â€” orchestrates ADMET -> scoring -> QUBO -> QAOA/Classical.
"""
import json
import logging
import time
from pathlib import Path
from typing import Dict, Any, List, Optional

import numpy as np
import pandas as pd

from app.config import get_settings
from app.services.admet_service import run_admet_screening, predict_toxicity, predict_solubility

logger = logging.getLogger(__name__)
settings = get_settings()

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent


def get_processed_dir() -> Path:
    p = Path(settings.data_processed_path).resolve()
    if not p.exists():
        p = PROJECT_ROOT / "data" / "processed"
    return p


def get_models_dir() -> Path:
    p = Path(settings.models_path).resolve()
    if not p.exists():
        p = PROJECT_ROOT / "models"
    return p


def run_quantum_optimization(
    n_candidates: int = 20,
    k_select: int = 5,
    qaoa_reps: int = 2,
    min_pic50: float = 7.0,
    max_tox_risk: float = 0.5,
    min_log_sol: float = -6.0,
    require_lipinski: bool = False,
    top_n_admet_input: int = 100,
) -> Dict[str, Any]:
    """
    Full quantum optimization pipeline:

    1. Load EGFR ML predictions
    2. Run ADMET screening (toxicity + solubility)
    3. Apply candidate filtering
    4. Compute composite scores
    5. Select top N for QUBO
    6. Run QAOA (statevector simulator)
    7. Run classical solver (same QUBO, brute-force)
    8. Compare results

    Returns complete result dict for storage in quantum_optimizations table.
    """
    from ml.admet.scoring import filter_candidates, prepare_quantum_candidates
    from quantum.qaoa_solver import run_qaoa
    from quantum.classical_solver import run_classical_solver

    start_total = time.time()

    # Step 1: Load EGFR ML dataset with predictions
    ml_path = get_processed_dir() / "EGFR_ML_dataset.csv"
    if not ml_path.exists():
        raise FileNotFoundError(
            "EGFR_ML_dataset.csv not found. Run Milestone 3 training first."
        )

    df_ml = pd.read_csv(ml_path)
    total_ml_molecules = len(df_ml)
    logger.info("Loaded %d molecules from EGFR ML dataset", total_ml_molecules)

    # Step 2: Run ADMET screening on top N by pIC50
    # Fallback: if RDKit is blocked by Application Control policy,
    # use pre-computed ADMET results file from prior successful run.
    admet_fallback_used = False
    try:
        df_admet = run_admet_screening(df_ml, top_n_input=top_n_admet_input)
    except (ImportError, OSError) as admet_err:
        logger.warning(
            "ADMET live screening failed (%s). Using pre-computed ADMET results.",
            admet_err,
        )
        admet_fallback_path = get_processed_dir() / "EGFR_admet_results.csv"
        if not admet_fallback_path.exists():
            raise FileNotFoundError(
                f"ADMET screening failed ({admet_err}) and no pre-computed "
                "EGFR_admet_results.csv found. Cannot proceed."
            ) from admet_err
        df_admet = pd.read_csv(admet_fallback_path)
        # Ensure column compatibility
        if "predicted_pIC50_for_score" in df_admet.columns and "predicted_pIC50" not in df_admet.columns:
            df_admet["predicted_pIC50"] = df_admet["predicted_pIC50_for_score"]
        admet_fallback_used = True
    n_admet_input = len(df_admet)

    # Step 3: Filter candidates
    df_filtered = filter_candidates(
        df_admet,
        min_pic50=min_pic50,
        max_tox_risk=max_tox_risk,
        min_log_sol=min_log_sol,
        require_lipinski=require_lipinski,
        top_n_before_filter=0,  # Already pre-filtered
    )
    n_after_filter = len(df_filtered)

    # Step 4: Select top N for quantum stage
    df_quantum = prepare_quantum_candidates(df_filtered, n_candidates=n_candidates)
    n_quantum_input = len(df_quantum)

    if n_quantum_input < k_select:
        raise ValueError(
            f"Only {n_quantum_input} candidate(s) survived filtering (min_pic50={min_pic50}), "
            f"but k_select={k_select} is required. Please lower min_pic50 or decrease k_select."
        )

    candidate_scores = df_quantum["composite_score"].values.astype(float)
    candidate_ids    = df_quantum["molecule_chembl_id"].tolist()

    logger.info(
        "Quantum stage: %d candidates (scores: min=%.3f, max=%.3f)",
        n_quantum_input, candidate_scores.min(), candidate_scores.max(),
    )

    # Step 5: Run QAOA (with graceful fallback when Qiskit is unavailable)
    qaoa_unavailable_reason: Optional[str] = None
    try:
        qaoa_result = run_qaoa(
            candidate_scores=candidate_scores,
            candidate_ids=candidate_ids,
            k_select=k_select,
            reps=qaoa_reps,
        )
    except (ImportError, OSError) as qiskit_err:
        # Qiskit native extension blocked by OS/AppControl policy or missing.
        # Degrade gracefully: fill qaoa_result with a structured "unavailable" stub
        # so the rest of the pipeline (classical solver, DB storage, API response)
        # still succeeds. The frontend can display a clear degraded-mode notice.
        qaoa_unavailable_reason = str(qiskit_err)
        logger.warning(
            "Qiskit unavailable (%s). Proceeding with classical solver only.", qaoa_unavailable_reason
        )
        # Build a stub result that mirrors the structure expected by the router
        x_stub = [0] * n_quantum_input
        for idx in sorted(range(n_quantum_input), key=lambda i: candidate_scores[i], reverse=True)[:k_select]:
            x_stub[idx] = 1
        selected_stub = [i for i, v in enumerate(x_stub) if v == 1]
        qaoa_result = {
            "algorithm": "QAOA (Unavailable)",
            "backend": "Unavailable — Qiskit blocked by Application Control policy",
            "simulator": False,
            "unavailable": True,
            "unavailable_reason": qaoa_unavailable_reason,
            "n_candidates": n_quantum_input,
            "k_select": k_select,
            "qaoa_reps": qaoa_reps,
            "optimizer": "N/A",
            "solution": x_stub,
            "qaoa_objective_value": 0.0,
            "qubo_objective_value": 0.0,
            "n_selected": len(selected_stub),
            "selected_indices": selected_stub,
            "selected_ids": [candidate_ids[i] for i in selected_stub],
            "selected_scores": [float(candidate_scores[i]) for i in selected_stub],
            "runtime_seconds": 0.0,
            "status": "UNAVAILABLE",
            "constraint_satisfied": False,
            "circuit_info": {"n_qubits": n_quantum_input, "qaoa_reps": qaoa_reps},
            "qubo_metadata": {},
            "qaoa_unavailable": qaoa_unavailable_reason is not None,
        "qaoa_unavailable_reason": qaoa_unavailable_reason,
        "disclaimer": (
                "QAOA could not run: Qiskit is blocked by an Application Control policy "
                "on this machine. Results shown are from the classical solver only."
            ),
        }

    # Step 6: Run classical solver
    classical_result = run_classical_solver(
        candidate_scores=candidate_scores,
        candidate_ids=candidate_ids,
        k_select=k_select,
    )

    # Step 7: Build candidate detail list (for DB storage)
    is_qaoa_unavail = qaoa_result.get("unavailable", False)
    qaoa_selected_set      = set() if is_qaoa_unavail else set(qaoa_result.get("selected_ids", []))
    classical_selected_set = set(classical_result.get("selected_ids", []))

    candidate_details = []
    for i, row in df_quantum.iterrows():
        mol_id = row["molecule_chembl_id"]
        candidate_details.append({
            "molecule_chembl_id":   mol_id,
            "smiles":               str(row.get("smiles", "")),
            "predicted_pIC50":      float(row.get("predicted_pIC50", row.get("pIC50", 0))),
            "tox_probability":      float(row.get("tox_probability", 0)),
            "predicted_log_solubility": float(row.get("predicted_log_solubility", -5)),
            "composite_score":      float(row.get("composite_score", 0)),
            "bioactivity_norm":     float(row.get("bioactivity_norm", 0)),
            "toxicity_risk_norm":   float(row.get("toxicity_risk_norm", 0)),
            "solubility_norm":      float(row.get("solubility_norm", 0)),
            "drug_likeness_norm":   float(row.get("drug_likeness_norm", 0)),
            "lipinski_pass":        bool(row.get("lipinski_pass", False)),
            "molecular_weight":     float(row.get("molecular_weight", 0)),
            "logP":                 float(row.get("logP", 0)),
            "selected_by_qaoa":     mol_id in qaoa_selected_set,
            "selected_by_classical": mol_id in classical_selected_set,
            "rank":                 i + 1,
        })

    total_runtime = time.time() - start_total

    return {
        "status": "COMPLETED" if qaoa_unavailable_reason is None else "CLASSICAL_ONLY",
        "pipeline": {
            "total_egfr_molecules":   total_ml_molecules,
            "admet_input_count":      n_admet_input,
            "after_filter_count":     n_after_filter,
            "quantum_input_count":    n_quantum_input,
        },
        "filter_config": {
            "min_pic50":          min_pic50,
            "max_tox_risk":       max_tox_risk,
            "min_log_sol":        min_log_sol,
            "require_lipinski":   require_lipinski,
            "top_n_admet_input":  top_n_admet_input,
        },
        "quantum_config": {
            "n_candidates":  n_candidates,
            "k_select":      k_select,
            "qaoa_reps":     qaoa_reps,
        },
        "qaoa_result":      qaoa_result,
        "classical_result": classical_result,
        "candidates":       candidate_details,
        "total_runtime_seconds": round(total_runtime, 4),
        "admet_fallback_used": admet_fallback_used,
        "qaoa_unavailable": qaoa_unavailable_reason is not None,
        "qaoa_unavailable_reason": qaoa_unavailable_reason,
        "disclaimer": (
            "ADMET predictions and quantum optimization results are computational outputs "
            "and do not constitute experimental or clinical validation. "
            "QAOA results do not establish quantum advantage unless supported by "
            "controlled benchmarking."
        ),
    }

