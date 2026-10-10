"""
Targets router.

Endpoints:
  GET  /api/targets            — List all available targets
  GET  /api/targets/{id}       — Get a single target by ID
  POST /api/targets            — Create a new target (authenticated)
"""
import logging
from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.routers.auth import get_current_user
from app.schemas.targets import TargetCreate, TargetResponse
from app.services.target_service import get_targets, get_target, create_target

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/targets", tags=["targets"])


@router.get("", response_model=List[TargetResponse])
def list_targets(db: Session = Depends(get_db)):
    """
    Return all available biological targets.
    Public endpoint — no authentication required.
    """
    return get_targets(db)


@router.get("/{target_id}", response_model=TargetResponse)
def get_target_by_id(target_id: int, db: Session = Depends(get_db)):
    """Return a single target by ID. Public endpoint."""
    return get_target(db, target_id)


@router.post("", response_model=TargetResponse, status_code=status.HTTP_201_CREATED)
def create_new_target(
    payload: TargetCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Create a new biological target.
    Authentication required.
    Returns 409 if ChEMBL ID already exists.
    """
    return create_target(db, payload)
