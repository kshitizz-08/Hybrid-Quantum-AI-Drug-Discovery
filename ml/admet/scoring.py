"""
ADMET Candidate Scoring Module.

Scoring Formula (fully documented):
====================================
Given per-molecule values:
  - picso         : predicted pIC50 (from EGFR Random Forest model)
  - tox_prob      : predicted toxicity probability (NR-AR, 0-1)
  - log_sol       : predicted log solubility (mol/L)
  - lipinski_pass : bool — passes Lipinski Rule of Five

Normalized components (all in [0, 1]):
  bioactivity_norm  = clip((pIC50 - 4.0) / 7.0, 0, 1)
  toxicity_risk_norm = tox_prob  (already in [0, 1]; 0 = safe, 1 = toxic)
  solubility_norm   = clip((log_sol - (-10.0)) / 12.0, 0, 1)  # -10 to +2
  drug_likeness_norm = 1.0 if lipinski_pass else 0.0

Final composite score:
  composite = (
      bioactivity_weight  * bioactivity_norm
    + solubility_weight   * solubility_norm
    + drug_likeness_weight * drug_likeness_norm
    - toxicity_weight     * toxicity_risk_norm
  )
  composite = clip(composite, 0, 1)

Default weights:
  bioactivity_weight   = 0.40
  toxicity_weight      = 0.30
  solubility_weight    = 0.20
  drug_likeness_weight = 0.10

The formula SUBTRACTS the toxicity component because high toxicity probability
reduces the overall score. High pIC50, high solubility, and low toxicity
all contribute positively.
"""
from typing import Dict, Optional
import numpy as np
import pandas as pd

from ml.admet.config import (
    SCORE_WEIGHTS,
    PIC50_NORM_MIN, PIC50_NORM_MAX,
    SOL_NORM_MIN, SOL_NORM_MAX,
    DEFAULT_CANDIDATE_COUNT, DEFAULT_QUANTUM_N, DEFAULT_QUANTUM_K,
    DEFAULT_MIN_PIC50, DEFAULT_MAX_TOX_RISK, DEFAULT_MIN_LOG_SOL,
    DEFAULT_REQUIRE_LIPINSKI,
)


def normalize_bioactivity(picso: float) -> float:
    """Normalize pIC50 to [0, 1]. Range: [4.0, 11.0]."""
    return float(np.clip((picso - PIC50_NORM_MIN) / (PIC50_NORM_MAX - PIC50_NORM_MIN), 0.0, 1.0))


def normalize_solubility(log_sol: float) -> float:
    """Normalize log solubility to [0, 1]. Range: [-10, +2]."""
    return float(np.clip((log_sol - SOL_NORM_MIN) / (SOL_NORM_MAX - SOL_NORM_MIN), 0.0, 1.0))


def compute_composite_score(
    picso: float,
    tox_prob: float,
    log_sol: float,
    lipinski_pass: bool,
    weights: Optional[Dict[str, float]] = None,
) -> Dict[str, float]:
    """
    Compute normalized composite drug candidate score.

    Returns dict with individual normalized components and final composite score.
    All values are in [0, 1].
    """
    w = weights if weights is not None else SCORE_WEIGHTS

    bioactivity_norm  = normalize_bioactivity(picso)
    tox_risk_norm     = float(np.clip(tox_prob, 0.0, 1.0))
    solubility_norm   = normalize_solubility(log_sol)
    drug_likeness_norm = 1.0 if lipinski_pass else 0.0

    composite = (
        w["bioactivity_weight"]   * bioactivity_norm
        + w["solubility_weight"]  * solubility_norm
        + w["drug_likeness_weight"] * drug_likeness_norm
        - w["toxicity_weight"]    * tox_risk_norm
    )
    composite = float(np.clip(composite, 0.0, 1.0))

    return {
        "bioactivity_norm":  round(bioactivity_norm, 4),
        "toxicity_risk_norm": round(tox_risk_norm, 4),
        "solubility_norm":   round(solubility_norm, 4),
        "drug_likeness_norm": round(drug_likeness_norm, 4),
        "composite_score":   round(composite, 4),
    }


def filter_candidates(
    df: pd.DataFrame,
    min_pic50: float = DEFAULT_MIN_PIC50,
    max_tox_risk: float = DEFAULT_MAX_TOX_RISK,
    min_log_sol: float = DEFAULT_MIN_LOG_SOL,
    require_lipinski: bool = DEFAULT_REQUIRE_LIPINSKI,
    top_n_before_filter: int = DEFAULT_CANDIDATE_COUNT,
) -> pd.DataFrame:
    """
    Apply configurable ADMET filtering to candidate molecules.

    Steps:
      1. Start from top N by predicted_pIC50 (pre-filter for ADMET)
      2. Apply min predicted pIC50 threshold
      3. Apply max toxicity risk (predicted probability)
      4. Apply min solubility threshold
      5. Optionally require Lipinski pass

    Returns filtered DataFrame sorted by composite_score descending.
    """
    # Start from pre-filtered top N
    working = df.copy()
    if top_n_before_filter > 0 and "predicted_pIC50" in working.columns:
        working = working.nlargest(top_n_before_filter, "predicted_pIC50")

    # Filter by pIC50
    if "predicted_pIC50" in working.columns:
        working = working[working["predicted_pIC50"] >= min_pic50]

    # Filter by toxicity risk
    if "tox_probability" in working.columns:
        working = working[working["tox_probability"] <= max_tox_risk]

    # Filter by solubility
    if "predicted_log_solubility" in working.columns:
        working = working[working["predicted_log_solubility"] >= min_log_sol]

    # Optional Lipinski filter
    if require_lipinski and "lipinski_pass" in working.columns:
        working = working[working["lipinski_pass"] == True]  # noqa: E712

    # Sort by composite score if available, else by predicted pIC50
    if "composite_score" in working.columns:
        working = working.sort_values("composite_score", ascending=False)
    elif "predicted_pIC50" in working.columns:
        working = working.sort_values("predicted_pIC50", ascending=False)

    return working.reset_index(drop=True)


def prepare_quantum_candidates(
    df_admet: pd.DataFrame,
    n_candidates: int = DEFAULT_QUANTUM_N,
) -> pd.DataFrame:
    """
    Select top N candidates (by composite_score) to enter the QUBO/QAOA stage.
    Returns a DataFrame with molecule IDs, scores, and component scores.
    """
    if "composite_score" in df_admet.columns:
        top = df_admet.nlargest(n_candidates, "composite_score").reset_index(drop=True)
    else:
        top = df_admet.head(n_candidates).reset_index(drop=True)

    return top
