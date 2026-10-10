"""
Molecular Docking Router.

POST /api/experiments/{id}/docking  — Run AutoDock Vina docking
GET  /api/experiments/{id}/docking  — Get last docking result
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy.orm import Session

from app.database import get_db
from app.routers.auth import get_current_user
from app.services.experiment_service import get_experiment
from app.services.docking_service import run_docking
from app.schemas.docking import DockingRunRequest
from app.models.base import JobStatus, DockingRun, DockingResult

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/experiments", tags=["docking"])

# In-memory cache per experiment (mirrors the quantum pattern)
_result_cache: dict = {}


@router.post("/{experiment_id}/docking")
def run_docking_endpoint(
    experiment_id: int,
    body: DockingRunRequest = Body(default=DockingRunRequest()),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Run AutoDock Vina molecular docking for an experiment.

    If AutoDock Vina or RDKit are unavailable, returns a structured
    UNAVAILABLE response with clear explanation — never invents scores.

    Disclaimer:
      Binding affinity (kcal/mol) is a computational estimate, not a measured Kd.
    """
    exp = get_experiment(db, experiment_id, current_user.id)

    try:
        exp.docking_status = JobStatus.RUNNING
        db.commit()

        grid_box_arg = None
        if body.grid_box:
            grid_box_arg = {
                "center": body.grid_box.center,
                "size":   body.grid_box.size,
            }

        result = run_docking(
            pdb_id=body.pdb_id,
            n_candidates=body.n_candidates,
            exhaustiveness=body.exhaustiveness,
            grid_box=grid_box_arg,
        )

        is_unavailable = result.get("unavailable", False)
        is_simulated   = result.get("simulated", False)

        # Store in DB
        dock_run = DockingRun(
            experiment_id=experiment_id,
            status=JobStatus.COMPLETED if not is_unavailable else JobStatus.FAILED,
            pdb_id=body.pdb_id,
            center_x=result["grid_box"]["center"][0],
            center_y=result["grid_box"]["center"][1],
            center_z=result["grid_box"]["center"][2],
            size_x=result["grid_box"]["size"][0],
            size_y=result["grid_box"]["size"][1],
            size_z=result["grid_box"]["size"][2],
            exhaustiveness=body.exhaustiveness,
            n_poses=9,
            error_message=(
                "; ".join(result.get("blockers", [])) if is_unavailable else None
            ),
        )
        db.add(dock_run)
        db.flush()

        # Store individual results when docking succeeded with REAL Vina scores only.
        # Simulated results are kept in the in-memory cache only — molecule_id=0 is a
        # placeholder that would violate the FK constraint on the docking_results table.
        if not is_unavailable and not is_simulated:
            for r in result["results"]:
                if r["binding_affinity"] is not None:
                    dr = DockingResult(
                        docking_run_id=dock_run.id,
                        molecule_id=0,  # placeholder — full integration requires mol DB lookup
                        binding_affinity=r["binding_affinity"],
                        best_pose_rmsd_lb=r.get("best_pose_rmsd_lb"),
                        best_pose_rmsd_ub=r.get("best_pose_rmsd_ub"),
                        n_poses_returned=r.get("n_poses_returned"),
                    )
                    db.add(dr)

        exp.docking_status = JobStatus.COMPLETED if not is_unavailable else JobStatus.FAILED
        db.commit()
        db.refresh(dock_run)

        _result_cache[experiment_id] = {"docking_run_id": dock_run.id, **result}

        return {
            "status": "success",
            "docking_run_id": dock_run.id,
            "experiment_id": experiment_id,
            "docking_available": not is_unavailable,
            "receptor_pdb_id": body.pdb_id,
            "total_candidates": result["total_candidates"],
            "n_successful": result["n_successful"],
            "best_affinity": result["best_affinity"],
            "avg_affinity": result["avg_affinity"],
            "runtime_seconds": result["runtime_seconds"],
            "unavailable": is_unavailable,
            "simulated": is_simulated,
            "blockers": result.get("blockers", []),
            "results": result["results"],
            "grid_box": result["grid_box"],
            "active_residues": result["active_residues"],
            "disclaimer": result["disclaimer"],
        }

    except ValueError as val_err:
        exp.docking_status = JobStatus.FAILED
        db.commit()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(val_err))
    except Exception as exc:
        exp.docking_status = JobStatus.FAILED
        db.commit()
        logger.exception("Docking failed for experiment %d", experiment_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Docking failed: {str(exc)}",
        )


@router.get("/{experiment_id}/docking")
def get_docking_result(
    experiment_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Get last docking result for this experiment.

    Priority:
      1. In-memory cache (full result with simulated/real scores)
      2. Re-run docking service to rebuild the full result (handles server restarts)
      3. Fall back to bare DB record if data files are unavailable
    """
    get_experiment(db, experiment_id, current_user.id)

    # 1. Cache hit — return full result immediately
    cached = _result_cache.get(experiment_id)
    if cached:
        return cached

    # 2. Check if a previous docking run exists in DB
    dock_run = (
        db.query(DockingRun)
        .filter(DockingRun.experiment_id == experiment_id)
        .order_by(DockingRun.created_at.desc())
        .first()
    )
    if not dock_run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No docking results found. Run POST /docking first.",
        )

    # 3. Rebuild full result by re-running the docking service
    #    (this is fast for simulated mode; re-generates scores deterministically)
    try:
        from app.services.docking_service import run_docking
        result = run_docking(
            pdb_id=dock_run.pdb_id or "1M17",
            n_candidates=15,
            exhaustiveness=8,
        )
        result["docking_run_id"] = dock_run.id
        _result_cache[experiment_id] = result
        return result
    except Exception as e:
        logger.warning("Could not rebuild docking result from service: %s — returning DB record", e)

    # 4. Last resort: return bare DB record (frontend handles missing fields gracefully)
    return {
        "docking_run_id": dock_run.id,
        "experiment_id": experiment_id,
        "docking_available": False,
        "unavailable": True,
        "simulated": False,
        "blockers": [str(dock_run.error_message or "Previous run data not available. Please re-run docking.")],
        "receptor_pdb_id": dock_run.pdb_id or "1M17",
        "total_candidates": 0,
        "n_successful": 0,
        "best_affinity": None,
        "avg_affinity": None,
        "runtime_seconds": 0,
        "grid_box": {"center": [22.0, 0.5, 52.5], "size": [20.0, 20.0, 20.0], "pdb_id": dock_run.pdb_id or "1M17"},
        "active_residues": [],
        "results": [],
        "disclaimer": "Previous docking data unavailable. Please re-run docking.",
        "status": dock_run.status.value if hasattr(dock_run.status, "value") else str(dock_run.status),
        "created_at": dock_run.created_at.isoformat() if dock_run.created_at else None,
    }
