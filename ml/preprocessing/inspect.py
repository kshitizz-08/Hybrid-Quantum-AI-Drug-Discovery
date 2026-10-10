"""
Dataset inspection utilities.

These functions analyse the raw EGFR dataset and return a structured
report without modifying any data. Safe to run multiple times.
"""
import logging
from typing import Dict, Any

import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


def inspect_dataset(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Produce a complete inspection report for the raw EGFR bioactivity dataset.

    Args:
        df: The raw DataFrame loaded from EGFR_bioactivity_raw.csv.

    Returns:
        A dictionary suitable for JSON serialization.
    """
    report: Dict[str, Any] = {}

    # ── Shape ─────────────────────────────────────────────────
    report["total_rows"]       = len(df)
    report["total_columns"]    = len(df.columns)
    report["column_names"]     = list(df.columns)

    # ── Unique molecules ──────────────────────────────────────
    report["unique_molecules"] = int(df["molecule_chembl_id"].nunique()) \
        if "molecule_chembl_id" in df.columns else None

    # ── SMILES ────────────────────────────────────────────────
    if "canonical_smiles" in df.columns:
        report["smiles_present"] = int(df["canonical_smiles"].notna().sum())
        report["smiles_missing"] = int(df["canonical_smiles"].isna().sum())
    else:
        report["smiles_present"] = None
        report["smiles_missing"] = None

    # ── Activity type distribution ────────────────────────────
    if "standard_type" in df.columns:
        report["standard_type_counts"] = df["standard_type"].value_counts().to_dict()
    else:
        report["standard_type_counts"] = {}

    # ── Units distribution ────────────────────────────────────
    if "standard_units" in df.columns:
        report["standard_units_counts"] = df["standard_units"].value_counts().to_dict()
    else:
        report["standard_units_counts"] = {}

    # ── IC50 value stats ──────────────────────────────────────
    if "standard_value" in df.columns:
        sv = pd.to_numeric(df["standard_value"], errors="coerce")
        report["standard_value_stats"] = {
            "count": int(sv.notna().sum()),
            "missing": int(sv.isna().sum()),
            "min": float(sv.min()) if sv.notna().any() else None,
            "max": float(sv.max()) if sv.notna().any() else None,
            "median": float(sv.median()) if sv.notna().any() else None,
            "mean": float(sv.mean()) if sv.notna().any() else None,
            "zero_or_negative": int((sv <= 0).sum()),
        }
    else:
        report["standard_value_stats"] = {}

    # ── pchembl_value (ChEMBL's pre-computed pIC50) ───────────
    if "pchembl_value" in df.columns:
        pv = pd.to_numeric(df["pchembl_value"], errors="coerce")
        report["pchembl_value_stats"] = {
            "present": int(pv.notna().sum()),
            "missing": int(pv.isna().sum()),
            "min": float(pv.min()) if pv.notna().any() else None,
            "max": float(pv.max()) if pv.notna().any() else None,
            "median": float(pv.median()) if pv.notna().any() else None,
        }
    else:
        report["pchembl_value_stats"] = {}

    # ── Duplicate flags ───────────────────────────────────────
    if "potential_duplicate" in df.columns:
        report["potential_duplicate_count"] = int(
            (df["potential_duplicate"] == 1).sum()
        )
    else:
        report["potential_duplicate_count"] = None

    # ── Data validity flags ───────────────────────────────────
    if "data_validity_comment" in df.columns:
        vc = df["data_validity_comment"].value_counts()
        report["data_validity_comments"] = vc.to_dict()
        report["data_validity_total_flagged"] = int(df["data_validity_comment"].notna().sum())
    else:
        report["data_validity_comments"] = {}
        report["data_validity_total_flagged"] = 0

    # ── Missing values summary ────────────────────────────────
    missing = df.isnull().sum()
    report["missing_values_per_column"] = {
        col: int(count)
        for col, count in missing.items()
        if count > 0
    }

    # ── Relation type ─────────────────────────────────────────
    if "standard_relation" in df.columns:
        report["standard_relation_counts"] = df["standard_relation"].value_counts().to_dict()
    else:
        report["standard_relation_counts"] = {}

    logger.info(
        "Dataset inspection complete: %d rows, %d unique molecules",
        report["total_rows"],
        report.get("unique_molecules", 0),
    )
    return report
