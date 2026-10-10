"""Pydantic schemas for Experiment request/response validation."""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, field_validator

from app.schemas.targets import TargetResponse


# ── Request schemas ───────────────────────────────────────────

class ExperimentCreate(BaseModel):
    name: str
    description: Optional[str] = None
    target_id: Optional[int] = None
    dataset_path: Optional[str] = None
    dataset_version: Optional[str] = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 3:
            raise ValueError("Experiment name must be at least 3 characters.")
        if len(v) > 300:
            raise ValueError("Experiment name must not exceed 300 characters.")
        return v


class ExperimentUpdate(BaseModel):
    """Partial update — all fields optional."""
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None


# ── Response schemas ──────────────────────────────────────────

class ExperimentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: Optional[str]
    status: str
    owner_id: int
    target_id: Optional[int]
    target: Optional[TargetResponse]
    dataset_path: Optional[str]
    dataset_version: Optional[str]
    raw_record_count: Optional[int]
    processed_record_count: Optional[int]
    preprocess_status: str
    screen_status: str
    quantum_status: str
    docking_status: str
    preprocessing_report: Optional[dict]
    created_at: datetime
    updated_at: Optional[datetime]
    completed_at: Optional[datetime]


class ExperimentListItem(BaseModel):
    """Lightweight version for list views."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: Optional[str]
    status: str
    target: Optional[TargetResponse]
    dataset_path: Optional[str]
    raw_record_count: Optional[int]
    processed_record_count: Optional[int]
    created_at: datetime
    updated_at: Optional[datetime]


# ── Stats schema ──────────────────────────────────────────────

class DashboardStats(BaseModel):
    total_experiments: int
    active_experiments: int
    completed_experiments: int
    failed_experiments: int
    total_targets: int
    total_molecules: int
    total_predictions: int
    total_docking_runs: int
