"""Pydantic schemas for Target request/response validation."""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, field_validator


class TargetCreate(BaseModel):
    name: str
    chembl_id: Optional[str] = None
    uniprot_id: Optional[str] = None
    organism: Optional[str] = None
    target_type: Optional[str] = None
    description: Optional[str] = None
    pdb_id: Optional[str] = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 2:
            raise ValueError("Target name must be at least 2 characters.")
        return v

    @field_validator("chembl_id")
    @classmethod
    def validate_chembl_id(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        v = v.strip().upper()
        if not v.startswith("CHEMBL"):
            raise ValueError("ChEMBL ID must start with 'CHEMBL' (e.g., CHEMBL203).")
        return v


class TargetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    chembl_id: Optional[str]
    uniprot_id: Optional[str]
    organism: Optional[str]
    target_type: Optional[str]
    description: Optional[str]
    pdb_id: Optional[str]
    created_at: datetime
