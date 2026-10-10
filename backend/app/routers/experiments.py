"""
Experiments router.

All endpoints enforce user ownership:
  A user can only access, modify, or delete their own experiments.

Endpoints:
  GET    /api/experiments/stats  — Dashboard statistics (authenticated)
  POST   /api/experiments        — Create experiment (authenticated)
  GET    /api/experiments        — List user's experiments (authenticated)
  GET    /api/experiments/{id}   — Get single experiment (authenticated)
  PATCH  /api/experiments/{id}   — Update experiment (authenticated)
  DELETE /api/experiments/{id}   — Delete experiment (authenticated)
"""
import logging
from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.routers.auth import get_current_user
from app.schemas.experiments import (
    ExperimentCreate,
    ExperimentUpdate,
    ExperimentResponse,
    ExperimentListItem,
    DashboardStats,
)
from app.services.experiment_service import (
    create_experiment,
    get_user_experiments,
    get_experiment,
    update_experiment,
    delete_experiment,
    get_dashboard_stats,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/experiments", tags=["experiments"])


@router.get("/stats", response_model=DashboardStats)
def dashboard_stats(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Return real dashboard statistics for the authenticated user.
    All counts are computed from live database queries — never hardcoded.
    """
    stats = get_dashboard_stats(db, current_user.id)
    return DashboardStats(**stats)


@router.post("", response_model=ExperimentResponse, status_code=status.HTTP_201_CREATED)
def create_new_experiment(
    payload: ExperimentCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Create a new drug discovery experiment owned by the authenticated user.
    The experiment starts in PENDING status with all pipeline stages as PENDING.
    """
    return create_experiment(db, current_user.id, payload)


@router.get("", response_model=List[ExperimentListItem])
def list_experiments(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Return all experiments owned by the authenticated user, newest first.
    """
    return get_user_experiments(db, current_user.id)


@router.get("/{experiment_id}", response_model=ExperimentResponse)
def get_single_experiment(
    experiment_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Return a single experiment.
    Returns 404 if not found OR if the experiment belongs to another user
    (to prevent information leakage).
    """
    return get_experiment(db, experiment_id, current_user.id)


@router.patch("/{experiment_id}", response_model=ExperimentResponse)
def update_single_experiment(
    experiment_id: int,
    payload: ExperimentUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Update an experiment's name, description, or status. Ownership enforced."""
    return update_experiment(db, experiment_id, current_user.id, payload)


@router.delete("/{experiment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_single_experiment(
    experiment_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Delete an experiment and all its cascaded data (molecules, predictions, etc.).
    Ownership enforced — returns 404 if not found or belongs to another user.
    """
    delete_experiment(db, experiment_id, current_user.id)
