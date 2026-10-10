"""
Target service — business logic for target management.

Targets are shared platform resources (not per-user).
The EGFR target is seeded automatically on startup.
"""
import logging
from typing import List, Optional

from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.base import Target
from app.schemas.targets import TargetCreate

logger = logging.getLogger(__name__)


def get_targets(db: Session) -> List[Target]:
    """Return all available targets ordered by name."""
    return db.query(Target).order_by(Target.name).all()


def get_target(db: Session, target_id: int) -> Target:
    """Return a single target by ID or raise 404."""
    target = db.query(Target).filter(Target.id == target_id).first()
    if not target:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Target with id={target_id} not found.",
        )
    return target


def get_target_by_chembl_id(db: Session, chembl_id: str) -> Optional[Target]:
    """Return target by ChEMBL ID or None."""
    return db.query(Target).filter(Target.chembl_id == chembl_id.upper()).first()


def create_target(db: Session, data: TargetCreate) -> Target:
    """
    Create a new target. Raises 409 if ChEMBL ID already exists.
    """
    if data.chembl_id:
        existing = get_target_by_chembl_id(db, data.chembl_id)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"A target with ChEMBL ID '{data.chembl_id}' already exists (id={existing.id}).",
            )

    target = Target(
        name=data.name,
        chembl_id=data.chembl_id,
        uniprot_id=data.uniprot_id,
        organism=data.organism,
        target_type=data.target_type,
        description=data.description,
        pdb_id=data.pdb_id,
    )
    db.add(target)
    db.commit()
    db.refresh(target)
    logger.info("Target created: id=%d name='%s' chembl_id='%s'", target.id, target.name, target.chembl_id)
    return target


def seed_egfr_target(db: Session) -> Target:
    """
    Idempotently ensure the EGFR target (CHEMBL203) exists in the database.

    This is called once at application startup. It will NOT overwrite
    an existing EGFR record.

    Source: ChEMBL Database — CHEMBL203
    Target: Epidermal Growth Factor Receptor (EGFR)
    """
    existing = get_target_by_chembl_id(db, "CHEMBL203")
    if existing:
        logger.debug("EGFR target already exists (id=%d). Skipping seed.", existing.id)
        return existing

    egfr = Target(
        name="Epidermal Growth Factor Receptor",
        chembl_id="CHEMBL203",
        uniprot_id="P00533",
        organism="Homo sapiens",
        target_type="Single Protein",
        description=(
            "The epidermal growth factor receptor (EGFR) is a receptor tyrosine kinase "
            "that plays a central role in regulating cell proliferation, differentiation, "
            "and survival. EGFR is overexpressed or mutated in several human cancers, "
            "making it a validated and well-studied drug target. The EGFR kinase domain "
            "is targeted by multiple approved tyrosine kinase inhibitors (TKIs) including "
            "erlotinib, gefitinib, and osimertinib. Source: ChEMBL Database (CHEMBL203)."
        ),
        pdb_id="1IVO",  # Representative EGFR crystal structure
    )
    db.add(egfr)
    db.commit()
    db.refresh(egfr)
    logger.info("EGFR target seeded successfully (id=%d, chembl_id=CHEMBL203).", egfr.id)
    return egfr
