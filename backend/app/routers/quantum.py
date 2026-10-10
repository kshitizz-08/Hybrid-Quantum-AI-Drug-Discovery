"""
Quantum Optimization Router.

POST /api/experiments/{id}/quantum  â€” Run QAOA + Classical optimization
GET  /api/experiments/{id}/quantum  â€” Get last optimization result
GET  /api/experiments/{id}/quantum/candidates â€” Get candidate details
"""
import json
import logging
from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy.orm import Session

from app.database import get_db
from app.routers.auth import get_current_user
from app.services.experiment_service import get_experiment
from app.services.quantum_service import run_quantum_optimization
from app.schemas.quantum import QuantumRunRequest
from app.models.base import JobStatus, ExperimentStatus

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/experiments", tags=["quantum"])

# In-memory cache for last optimization result per experiment (simple approach)
# In production, store in DB using quantum_optimizations table
_result_cache: dict = {}


@router.post("/{experiment_id}/quantum")
def run_quantum(
    experiment_id: int,
    body: QuantumRunRequest = Body(default=QuantumRunRequest()),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Run QAOA-based drug candidate optimization.

    Pipeline:
      1. Load EGFR ML predictions
      2. Run ADMET screening (toxicity + solubility)
      3. Apply configurable candidate filtering
      4. Build QUBO (maximize composite score, select K from N)
      5. Run QAOA (StatevectorSampler simulator, not real hardware)
      6. Run classical exact solver (same QUBO, brute-force comparison)
      7. Store and return results

    Disclaimer:
      Results are from simulation. No quantum advantage is claimed.
    """
    exp = get_experiment(db, experiment_id, current_user.id)

    try:
        exp.quantum_status = JobStatus.RUNNING
        db.commit()

        result = run_quantum_optimization(
            n_candidates=body.n_candidates,
            k_select=body.k_select,
            qaoa_reps=body.qaoa_reps,
            min_pic50=body.min_pic50,
            max_tox_risk=body.max_tox_risk,
            min_log_sol=body.min_log_sol,
            require_lipinski=body.require_lipinski,
            top_n_admet_input=body.top_n_admet_input,
        )

        # Store in DB quantum_optimizations table
        from app.models.base import QuantumOptimization
        qaoa_r = result["qaoa_result"]
        classical_r = result["classical_result"]

        is_unavailable = qaoa_r.get("unavailable", False)
        qopt = QuantumOptimization(
            experiment_id=experiment_id,
            status=JobStatus.COMPLETED,
            n_candidates_input=result["pipeline"]["quantum_input_count"],
            n_candidates_selected=classical_r["n_selected"] if is_unavailable else qaoa_r["n_selected"],
            qaoa_depth=body.qaoa_reps,
            backend_type="classical_fallback" if is_unavailable else "simulator",
            backend_name=classical_r["backend"] if is_unavailable else qaoa_r["backend"],
            bioactivity_weight=0.40,
            diversity_weight=0.00,
            drug_likeness_weight=0.10,
            classical_objective_value=classical_r["classical_objective_value"],
            qaoa_objective_value=qaoa_r["qaoa_objective_value"],
            classical_runtime_seconds=classical_r["runtime_seconds"],
            qaoa_runtime_seconds=qaoa_r["runtime_seconds"],
            qubo_matrix=result["classical_result"].get("qubo_metadata") or result["qaoa_result"].get("qubo_metadata"),
            qaoa_result_raw=result,
        )
        db.add(qopt)

        exp.quantum_status = JobStatus.COMPLETED
        exp.status = ExperimentStatus.RUNNING
        db.commit()
        db.refresh(qopt)

        # Cache result for GET endpoint
        _result_cache[experiment_id] = {"optimization_id": qopt.id, **result}

        return {
            "status": "success",
            "optimization_id": qopt.id,
            "experiment_id": experiment_id,
            "summary": {
                "egfr_molecules":      result["pipeline"]["total_egfr_molecules"],
                "admet_screened":      result["pipeline"]["admet_input_count"],
                "after_filter":        result["pipeline"]["after_filter_count"],
                "quantum_input":       result["pipeline"]["quantum_input_count"],
                "qaoa_selected":       qaoa_r["n_selected"],
                "qaoa_objective":      qaoa_r["qaoa_objective_value"],
                "classical_objective": classical_r["classical_objective_value"],
                "qaoa_runtime_s":      qaoa_r["runtime_seconds"],
                "classical_runtime_s": classical_r["runtime_seconds"],
                "constraint_ok":       qaoa_r["constraint_satisfied"],
                "backend":             qaoa_r["backend"],
                "qaoa_unavailable":    result.get("qaoa_unavailable", False),
                "qaoa_unavailable_reason": result.get("qaoa_unavailable_reason"),
                "mode":                result.get("status", "COMPLETED"),
            },
            "disclaimer": result["disclaimer"],
        }

    except ValueError as val_err:
        exp.quantum_status = JobStatus.FAILED
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(val_err),
        )
    except Exception as exc:
        exp.quantum_status = JobStatus.FAILED
        db.commit()
        logger.exception("Quantum optimization failed for experiment %d", experiment_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Quantum optimization failed: {str(exc)}",
        )


@router.get("/{experiment_id}/quantum")
def get_quantum_result(
    experiment_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get last quantum optimization result for this experiment."""
    get_experiment(db, experiment_id, current_user.id)

    from app.models.base import QuantumOptimization
    qopt = (
        db.query(QuantumOptimization)
        .filter(QuantumOptimization.experiment_id == experiment_id)
        .order_by(QuantumOptimization.created_at.desc())
        .first()
    )

    if not qopt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No quantum optimization found. Run POST /quantum first.",
        )

    cached = _result_cache.get(experiment_id, {})
    raw = qopt.qaoa_result_raw or cached

    return {
        "experiment_id":     experiment_id,
        "optimization_id":   qopt.id,
        "status":            qopt.status.value if hasattr(qopt.status, "value") else str(qopt.status),
        "backend":           qopt.backend_name,
        "n_candidates_input":   qopt.n_candidates_input,
        "n_candidates_selected": qopt.n_candidates_selected,
        "qaoa_reps":         qopt.qaoa_depth,
        "qaoa_objective":    qopt.qaoa_objective_value,
        "classical_objective": qopt.classical_objective_value,
        "qaoa_runtime_s":    qopt.qaoa_runtime_seconds,
        "classical_runtime_s": qopt.classical_runtime_seconds,
        "created_at":        qopt.created_at.isoformat() if qopt.created_at else None,
        "pipeline": raw.get("pipeline", {}),
        "quantum_config": raw.get("quantum_config", {}),
        "filter_config": raw.get("filter_config", {}),
        "qaoa_result": raw.get("qaoa_result", {}),
        "classical_result": raw.get("classical_result", {}),
        "disclaimer": raw.get("disclaimer", ""),
    }


@router.get("/{experiment_id}/quantum/candidates")
def get_quantum_candidates(
    experiment_id: int,
    selected_only: bool = False,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Get candidate molecules that entered the QUBO/QAOA optimization,
    with QAOA and classical selection flags.
    """
    get_experiment(db, experiment_id, current_user.id)

    cached = _result_cache.get(experiment_id)
    if not cached:
        from app.models.base import QuantumOptimization
        qopt = (
            db.query(QuantumOptimization)
            .filter(QuantumOptimization.experiment_id == experiment_id)
            .order_by(QuantumOptimization.created_at.desc())
            .first()
        )
        if not qopt or not qopt.qaoa_result_raw:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No quantum optimization candidates found.",
            )
        cached = qopt.qaoa_result_raw

    candidates = cached.get("candidates", [])
    if selected_only:
        candidates = [c for c in candidates if c.get("selected_by_qaoa") or c.get("selected_by_classical")]

    return {
        "experiment_id":   experiment_id,
        "total_candidates": len(cached.get("candidates", [])),
        "returned":        len(candidates),
        "selected_only":   selected_only,
        "candidates":      candidates,
    }

