"""
Experiment service — business logic for experiment management.

All operations enforce user ownership:
  - A user can only read/modify/delete their own experiments.
  - User isolation is checked in every relevant function.
"""
import logging
from typing import List, Optional
from datetime import datetime

from sqlalchemy.orm import Session, joinedload
from fastapi import HTTPException, status

from app.models.base import (
    Experiment, ExperimentStatus, JobStatus,
    Molecule, Prediction, DockingRun, Target,
)
from app.schemas.experiments import ExperimentCreate, ExperimentUpdate

logger = logging.getLogger(__name__)

# Default dataset information for the EGFR project
EGFR_DATASET_PATH = "data/raw/EGFR_bioactivity_raw.csv"
EGFR_DATASET_VERSION = "chembl_33"


def create_experiment(db: Session, user_id: int, data: ExperimentCreate) -> Experiment:
    """
    Create a new experiment owned by `user_id`.
    Status defaults to DRAFT.
    All pipeline stages default to PENDING.
    """
    # Validate target exists if provided
    if data.target_id:
        target = db.query(Target).filter(Target.id == data.target_id).first()
        if not target:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Target with id={data.target_id} not found.",
            )

    # Use EGFR dataset as default if no path specified
    dataset_path = data.dataset_path or EGFR_DATASET_PATH
    dataset_version = data.dataset_version or EGFR_DATASET_VERSION

    experiment = Experiment(
        name=data.name,
        description=data.description,
        owner_id=user_id,
        target_id=data.target_id,
        dataset_path=dataset_path,
        dataset_version=dataset_version,
        status=ExperimentStatus.PENDING,
        preprocess_status=JobStatus.PENDING,
        screen_status=JobStatus.PENDING,
        quantum_status=JobStatus.PENDING,
        docking_status=JobStatus.PENDING,
    )
    db.add(experiment)
    db.commit()
    db.refresh(experiment)
    logger.info(
        "Experiment created: id=%d name='%s' owner_id=%d",
        experiment.id, experiment.name, user_id
    )
    return experiment


def get_user_experiments(db: Session, user_id: int) -> List[Experiment]:
    """
    Return all experiments belonging to user_id, newest first.
    Eagerly loads the related target to avoid N+1 queries.
    """
    return (
        db.query(Experiment)
        .options(joinedload(Experiment.target))
        .filter(Experiment.owner_id == user_id)
        .order_by(Experiment.created_at.desc())
        .all()
    )


def get_experiment(db: Session, experiment_id: int, user_id: int) -> Experiment:
    """
    Return a single experiment.
    Raises 404 if not found, 403 if the requesting user does not own it.
    """
    experiment = (
        db.query(Experiment)
        .options(joinedload(Experiment.target))
        .filter(Experiment.id == experiment_id)
        .first()
    )

    if experiment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Experiment with id={experiment_id} not found.",
        )

    if experiment.owner_id != user_id:
        # Return 404 (not 403) to avoid leaking existence of other users' data
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Experiment with id={experiment_id} not found.",
        )

    return experiment


def update_experiment(
    db: Session,
    experiment_id: int,
    user_id: int,
    data: ExperimentUpdate,
) -> Experiment:
    """Update an experiment's name, description, or status. Ownership enforced."""
    experiment = get_experiment(db, experiment_id, user_id)

    if data.name is not None:
        experiment.name = data.name.strip()
    if data.description is not None:
        experiment.description = data.description
    if data.status is not None:
        try:
            experiment.status = ExperimentStatus(data.status)
        except ValueError:
            valid = [s.value for s in ExperimentStatus]
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid status '{data.status}'. Valid values: {valid}.",
            )
        if data.status == ExperimentStatus.COMPLETED.value:
            experiment.completed_at = datetime.utcnow()

    experiment.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(experiment)
    return experiment


def delete_experiment(db: Session, experiment_id: int, user_id: int) -> None:
    """
    Delete an experiment and all its cascaded data.
    Raises 404 if not found or not owned by user.
    """
    experiment = get_experiment(db, experiment_id, user_id)
    db.delete(experiment)
    db.commit()
    logger.info("Experiment deleted: id=%d by user_id=%d", experiment_id, user_id)


def get_dashboard_stats(db: Session, user_id: int) -> dict:
    """
    Return dashboard statistics for a specific user.
    All counts come from real database queries — never hardcoded.
    """
    user_experiments = db.query(Experiment).filter(Experiment.owner_id == user_id)

    total = user_experiments.count()
    active = user_experiments.filter(
        Experiment.status.in_([ExperimentStatus.RUNNING, ExperimentStatus.PENDING])
    ).count()
    completed = user_experiments.filter(
        Experiment.status == ExperimentStatus.COMPLETED
    ).count()
    failed = user_experiments.filter(
        Experiment.status == ExperimentStatus.FAILED
    ).count()

    # Count molecules that belong to this user's experiments
    total_molecules = (
        db.query(Molecule)
        .join(Experiment, Molecule.experiment_id == Experiment.id)
        .filter(Experiment.owner_id == user_id)
        .count()
    )

    # Count predictions that belong to this user's experiments
    total_predictions = (
        db.query(Prediction)
        .join(Experiment, Prediction.experiment_id == Experiment.id)
        .filter(Experiment.owner_id == user_id)
        .count()
    )

    # Count docking runs for this user's experiments
    total_docking_runs = (
        db.query(DockingRun)
        .join(Experiment, DockingRun.experiment_id == Experiment.id)
        .filter(Experiment.owner_id == user_id)
        .count()
    )

    # Total targets (platform-wide — shared resource)
    total_targets = db.query(Target).count()

    return {
        "total_experiments": total,
        "active_experiments": active,
        "completed_experiments": completed,
        "failed_experiments": failed,
        "total_targets": total_targets,
        "total_molecules": total_molecules,
        "total_predictions": total_predictions,
        "total_docking_runs": total_docking_runs,
    }
