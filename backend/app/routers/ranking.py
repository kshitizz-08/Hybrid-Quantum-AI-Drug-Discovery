"""
Final Ranking Router — M6.

POST /api/experiments/{id}/ranking  — Compute final candidate rankings
GET  /api/experiments/{id}/ranking  — Get cached rankings
GET  /api/experiments/{id}/ranking/csv — Download ranked candidates as CSV
"""
import csv
import io
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Body, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from app.database import get_db
from app.routers.auth import get_current_user
from app.services.experiment_service import get_experiment
from app.services.ranking_service import run_final_ranking, DEFAULT_WEIGHTS

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/experiments", tags=["ranking"])

_result_cache: dict = {}


class RankingRequest(BaseModel):
    weights: Optional[dict] = Field(
        None,
        description="Component weights dict. Keys: bioactivity, drug_likeness, toxicity, solubility, quantum, docking",
        example={
            "bioactivity": 0.35, "drug_likeness": 0.20,
            "toxicity": 0.20, "solubility": 0.10, "quantum": 0.15, "docking": 0.00,
        },
    )
    include_docking: bool = Field(
        False,
        description="If True, includes docking data from the last docking run (if available).",
    )


@router.post("/{experiment_id}/ranking")
def compute_ranking(
    experiment_id: int,
    body: RankingRequest = Body(default=RankingRequest()),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Compute final weighted composite scores and rank all candidates.

    Methodology is fully documented in ranking_service.py. Missing data
    components (docking) are excluded from the formula — not imputed as zero.
    """
    exp = get_experiment(db, experiment_id, current_user.id)

    try:
        # Load docking results if requested and available (real OR simulated)
        docking_results = None
        docking_is_simulated = False
        if body.include_docking:
            from app.routers.docking import _result_cache as dock_cache
            dock_data = dock_cache.get(experiment_id, {})
            # Accept results that are either real (not unavailable) or simulated
            has_scores = (
                dock_data
                and not dock_data.get("unavailable", True)
                and dock_data.get("results")
            )
            if has_scores:
                docking_results = dock_data.get("results", [])
                docking_is_simulated = dock_data.get("simulated", False)

        result = run_final_ranking(
            weights=body.weights,
            docking_results=docking_results,
            docking_is_simulated=docking_is_simulated,
            experiment_id=experiment_id,
        )

        _result_cache[experiment_id] = result
        return result

    except FileNotFoundError as fe:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(fe))
    except Exception as exc:
        logger.exception("Ranking failed for experiment %d", experiment_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ranking failed: {str(exc)}",
        )


@router.get("/{experiment_id}/ranking")
def get_ranking(
    experiment_id: int,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get cached final ranking for an experiment, with pagination."""
    get_experiment(db, experiment_id, current_user.id)

    cached = _result_cache.get(experiment_id)
    if not cached:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No ranking found. Run POST /ranking first.",
        )

    candidates = cached.get("candidates", [])
    paged = candidates[offset : offset + limit]

    return {
        **{k: v for k, v in cached.items() if k != "candidates"},
        "total": len(candidates),
        "offset": offset,
        "limit": limit,
        "candidates": paged,
    }


@router.get("/{experiment_id}/ranking/csv")
def download_ranking_csv(
    experiment_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Download the ranked candidates as a CSV file."""
    get_experiment(db, experiment_id, current_user.id)

    cached = _result_cache.get(experiment_id)
    if not cached:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No ranking found. Run POST /ranking first.",
        )

    candidates = cached.get("candidates", [])
    if not candidates:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No candidates to export.")

    output = io.StringIO()
    fieldnames = [
        "rank", "molecule_chembl_id", "smiles", "predicted_pIC50",
        "tox_probability", "predicted_log_solubility", "lipinski_pass",
        "molecular_weight", "logP", "composite_score",
        "bioactivity_score_norm", "drug_likeness_score_norm",
        "toxicity_score_norm", "solubility_score_norm", "quantum_score_norm",
        "docking_score_norm", "docking_affinity_kcal", "final_score",
    ]
    writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    for c in candidates:
        writer.writerow(c)

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=egfr_ranked_candidates_exp{experiment_id}.csv"
        },
    )
